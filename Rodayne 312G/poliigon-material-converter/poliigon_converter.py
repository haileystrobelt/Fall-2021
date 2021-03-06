# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import json
import os
import re

import bpy
import mathutils


# -----------------------------------------------------------------------------
# STATIC STRINGS (for regex matching)
# -----------------------------------------------------------------------------


# searches for e.g. the _2K_ in "sometext_2K_moretext" or "..._14K.png"
# negative lookahead is why the code is duplicated within the (?! )
SEARCH_SIZE = r"[-_ ]{1}[0-9]{1,3}[kK]{1}[-_ .]{1}(?!.*[-_ ]{1}[0-9]{1,3}[kK]{1}[-_ .]{1})"
# get HIRES from e.g. setname_GLOSS_HIRES.jpeg, negative lookahead
SEARCH_HIRES = r"(?i)[-_ ]{1}(HIRES)(?!.*[-_ ]{1}(HIRES)[.]{1})"

# determines if METALNESS or SPECULAR (not case sensitive) at end of filename
SPEC_WORKFLOW = r"(?i)SPECULAR[.]{1}[a-zA-Z]{3}(?!.*SPECULAR[.]{1}[a-zA-Z]{3})"
METAL_WORKFLOW = r"(?i)METALNESS[.]{1}[a-zA-Z]{3}(?!.*METALNESS[.]{1}[a-zA-Z]{3})"

# Detects if basepath has REFLECTION or GLOSS pass
GLOSS_REFLECT_PASS = r"(?i)[-_ ]{1}(GLOSS|REFLECTION|REFL)[-_ ]{1}"

# e.g. find material_NRM_ out of material_NRM_2K, or find
# material_NRM-2K- out of material_NRM-2K-METALNESS
MATCH_BEFORE_LAST_SEPARATOR = r"^(.*[-_ ])"

# find any VAR# within pass, to help prefer lowest variance type for given texture
# (consider implementing negative lookahead)
SEARCH_VAR = r"(?i)[-_ ]{1}var[0-9]{1,2}[-_ ]{1}"

# fallback search for preview, if not in preview folder
SEARCH_THUMB = r"(?i)[-_ ]{1}(PREVIEW|THUMB|THUMBNAIL|ICON)[-_ .]{1}"

# for determining whether to auto-assign the rug falloff shader
RUG_NAMES = ["carpet", "rug", "fabric"]

# -----------------------------------------------------------------------------
# INTERNAL METHODS/CLASSES
# -----------------------------------------------------------------------------


class PMC_workflow():
	"""
	Supports the building of materials and detecting of material sets

	While some functions are used to identify multiple material sets from a
	directory, the internally used variables and parameters are configured
	to be specific to a single material set
	"""

	def __init__(self,
			use_ao=True,
			use_disp=True,
			use_bump=True,
			use_sixteenbit=False,
			verbose=True,
			conform_uv=True,
			microdisp=False,
			mapping='uv_simple_mapping'):
		self.engine = None # see below
		self.workflow = None # one of: METALNESS or SPECULAR
		self.material = None # material ID block once created
		self.setname = None # path to base set, but including size
		self.status = {} # for storing status such as errors or other info
		self.passes = self.pass_names()
		self.size = None # numeric size of pass, or HIRES
		self.setpath = None

		self.use_ao=use_ao
		self.use_disp=use_disp
		self.use_bump=use_bump
		self.use_sixteenbit=use_sixteenbit
		self.conform_uv=conform_uv
		self.microdisp = microdisp
		self.mapping = mapping  # Enum, see items in poliigon_ops_props.py

		# auto set workflow based on render engine and
		# if Principled BSDF in node types, and engine==Cycles, set "cycles_principled"
		# for now, just using:
		self.engine = "cycles_principled"

		self.mapping_name_mosaic = "MosaicUVMapping" # name / id to give mosaic node
		self.mapping_name_simple = "SimpleUVMapping"
		self.mixer_name = "PBR Mixer"

		# provide extra logging information
		addon_prefs = get_preferences()
		if not addon_prefs:
			self.verbose = True
		else:
			self.verbose = addon_prefs.verbose

	def __repr__(self):
		return "<pmc_workflow module>"
	def __str__(self):
		return "Poliigon material loader, with workflow:{}, material:{}, and setname:{}".format(
			self.workflow,self.material,self.setname)

	# define the allowed passname types
	class pass_names():
		def __init__(self):
			self.COLOR = None
			self.BUMP = None
			self.DISPLACEMENT = None
			self.GLOSS = None
			self.NORMAL = None
			self.METALNESS = None
			self.ROUGHNESS = None
			self.AO = None
			self.DIRT = None # not yet used
			self.SSS = None
			self.THUMBNAIL = None # not yet used
			self.ALPHAMASKED = None # full color with alpha channel
			self.ALPHA = None # black and white
			self.TRANSMISSION = None

		def __repr__(self):
			return "<pmc_workflow material passes filenames>"

		# define properties to expand names to match,
		# so that you can detect any of COLOR, COL, etc and it maps correctly
		# while still using the class structure

		@property
		def COL(self):
			return self.COLOR
		@COL.setter
		def COL(self, value):
			self.COLOR = value

		@property
		def DISP(self):
			return self.DISPLACEMENT
		@DISP.setter
		def DISP(self, value):
			self.DISPLACEMENT = value

		@property
		def MASK(self):
			return self.ALPHA
		@MASK.setter
		def MASK(self, value):
			self.ALPHA = value

		@property
		def NRM(self):
			return self.NORMAL
		@NRM.setter
		def NRM(self, value):
			self.NORMAL = value

		@property
		def NORMALS(self):
			return self.NORMAL
		@NORMALS.setter
		def NORMALS(self, value):
			self.NORMAL = value

		# @property
		# def REFL(self):
		# 	return self.REFLECTION
		# @REFL.setter
		# def REFL(self, value):
		# 	self.REFLECTION = value

		@property
		def METAL(self):
			return self.METALNESS
		@METAL.setter
		def METAL(self, value):
			self.METALNESS = value

	def save_settings_to_props(self):
		if self.material is None:
			return
		self.material.pmc_matprops.workflow = self.workflow
		# self.material.pmc_matprops.engine = self.engine # not needed
		self.material.pmc_matprops.setname = self.setname
		self.material.pmc_matprops.status = json.dumps(self.status)
		self.material.pmc_matprops.size = "" if self.size==None else self.size
		self.material.pmc_matprops.use_ao = self.use_ao
		self.material.pmc_matprops.use_disp = self.use_disp
		self.material.pmc_matprops.use_bump = self.use_bump
		self.material.pmc_matprops.use_sixteenbit = self.use_sixteenbit
		self.material.pmc_matprops.setpath = self.setpath

	def get_passes(self):
		"""
		Narrow list of prop types of valid pass names for image names
		Only inludes properties defined in __init__
		"""
		return list(self.passes.__dict__) # vars(self.passes) also works

	def get_passes_loose_names(self):
		"""
		Wide list of prop types of valid pass names for image names
		Includes e.g. both COLOR and COL
		"""
		return [prop for prop in dir(self.passes) if "__" not in prop]

	def get_sets_from_filenames(self, files):
		"""
		Returns all unique set base names for materials given provided files
		:files: list of full (relative or absolute) filepaths, not dirs
		"""

		addon_prefs = get_preferences()
		if not addon_prefs:
			verbose = None
		else:
			verbose = addon_prefs.verbose

		# valid set names
		sets = []

		# each file added could potentially be it's own set
		for file in files:

			# first check if a valid set member
			base = os.path.basename(file)
			dirname = os.path.dirname(file)
			valid = False
			setbreak = ""

			# skip hidden files
			if base.startswith("."):
				continue

			# see if it's a METALNESS workflow type, as opposed to just
			# the METALNESS pass of a material flow
			# Assumption: METALNESS workflow type always identified via
			# "METALNESS" or "SPECULAR" at end of filename
			if (os.path.splitext(base)[0]).endswith("METALNESS"):
				# remove the METALNESS from end of path name, also
				# acknowledging this drops extension: os.path.splitext(base)[1]
				base = (os.path.splitext(base)[0])[:-len("METALNESS")]
			elif(os.path.splitext(base)[0]).endswith("SPECULAR"):
				base = (os.path.splitext(base)[0])[:-len("SPECULAR")]

			for itm in PMC_workflow().get_passes_loose_names():
				if "_"+itm in base:
					valid=True
					setbreak = "_"+itm
					break
				elif "-"+itm in base:
					valid=True
					setbreak = "-"+itm
					break
				elif " "+itm in base:
					valid=True
					setbreak = " "+itm
					break

			if valid is False:
				base_end = os.path.splitext(base)[0].lower()
				is_preview = False
				for itm in ("sphere", "flat", "cube"):
					if base_end.endswith(itm):
						is_preview = True
						break
				if verbose and not is_preview:
					print("Poliigon: Skipping non-valid set member "+file)
					print("\t", base_end)
				continue

			# get setname
			setname = base.split(setbreak)[0]
			setname = os.path.join(dirname,setname)

			# add size component to set name
			m = re.search(SEARCH_SIZE,os.path.basename(base))
			hi = re.search(SEARCH_HIRES,os.path.basename(base))
			if m:
				tmpsize = m.group(0)[:-1] # cut off the _ after k
				setname += tmpsize
				if setname not in sets: sets.append(setname)
			elif hi:
				setname += hi.group(0)
				if setname not in sets: sets.append(setname)
			else:
				print("Poliigon: Set missing texture size information (skipping):")
				print("\t", file, "- setname:", setname)
				# could potentially still add as set here.. if no size..

		return sets

	def get_thumbnail(self, thumbnail_type="sphere"):
		"""Get the best thumbnail file for set

		Args:
			thumbnail_type: Enum value from set (sphere, flat, cube)
		Returns:
			Filepath string or None
		"""

		if thumbnail_type not in ("sphere", "flat", "cube"):
			raise Exception("Invalid thumbnail type "+thumbnail_type)

		# first search in ../previews folder, then in same folder
		set_path_presize = re.search(MATCH_BEFORE_LAST_SEPARATOR,
							self.setpath).group(0)[:-1] # remove last "-_ "
		dirname = os.path.dirname(set_path_presize)
		par_dirname = os.path.dirname(dirname)

		# find all valid folders to find icons
		parent_folders_ref = ["previews", "preview", "thumbnail", "icon"]
		parent_folders = [dirname]
		thumbnails = []
		icon_path = None

		parent_folders += [os.path.join(par_dirname, matchdir)
				for matchdir in os.listdir(par_dirname)
				if (os.path.isdir(os.path.join(par_dirname, matchdir)))
				and matchdir.lower() in parent_folders_ref]

		# Look one further folder up as well, needed for metal and specular workflows
		parpar_dirname = os.path.dirname(par_dirname)
		parent_folders += [os.path.join(parpar_dirname, matchdir)
				for matchdir in os.listdir(parpar_dirname)
				if (os.path.isdir(os.path.join(parpar_dirname, matchdir)))
				and matchdir.lower() in parent_folders_ref]

		if self.size:
			sub_setname = str(self.setname)[:-len(self.size)-1]
		else:
			sub_setname = str(self.setname)
		for folder in parent_folders:
			thumbnails = [
				setfile for setfile in os.listdir(folder)
				if (os.path.isfile(os.path.join(folder, setfile)))
				and re.search(
					r"(?i)" + sub_setname + r"[-_ .]{1}" + thumbnail_type,
					setfile)
				]
			if thumbnails:
				icon_path = os.path.join(folder, thumbnails[0])
				break

		# Fallback to a color pass for preview
		if not icon_path and self.verbose:
			print("No target icon found for {} of type {}".format(
				self.setpath, thumbnail_type))
		if not icon_path and self.passes.ALPHAMASKED:
			icon_path = self.passes.ALPHAMASKED
		elif not icon_path and self.passes.COLOR:
			icon_path = self.passes.COLOR

		return icon_path

	def set_relative(self):
		"""Set all images used in material to be relative"""
		if self.verbose:
			print("Trying to make relative paths")
		imgs = [n.image for n in self.material.node_tree.nodes
				if n.type=="TEX_IMAGE"]
		for img in imgs:
			img.filepath = bpy.path.relpath(img.filepath)

	def splitMaterialName(self, name):
		"""Split a material name into words

		Skips HIRES (caps) as it is not recognized in website
		"""
		# result should: split on lowerCap mix, spaces, extensions,
		# channel names (last one found only), and numbers (keep the # tho)

		res = re.split(r"[-_ .]|[0-9]{1,2}[kK]", name.replace("HIRES", ""))
		resb = []
		for a in res:
			if len(a)==0:
				continue
			# Split by cap case and numbers
			a = re.findall('[A-Z][^A-Z0-9]*|[0-9]{1,}',a)
			resb += a
		return resb

	def build_material_from_set(self, context, set_path, dryrun=False):
		"""Builds all materials given a file sets

		Returns:
			status, material ID
		"""

		addon_prefs = get_preferences(context)
		if not addon_prefs:
			verbose = None
		else:
			verbose = addon_prefs.verbose

		# note that: set_path has e.g. -2K or _10K etc at end, and nothing after
		set_path_presize = re.search(MATCH_BEFORE_LAST_SEPARATOR,
							set_path).group(0)[:-1] # remove last "-_ "

		cmpsize = set_path[len(set_path_presize)+1:] # ie 4K of .._4K
		set_presize = os.path.basename(set_path_presize)
		dirname = os.path.dirname(set_path_presize)

		# clear existing workflow settings
		self.status = {}
		self.setpath = set_path
		self.setname = os.path.basename(set_path)
		self.workflow = None
		self.size = None
		self.passes = self.pass_names()
		self.material = None

		# For prod, keep options for verbose logging here
		if verbose:
			print("\nPoliigon: MATERIAL BUILD PARAMETERS")
			print("\tSetname:",self.setname)
			print("\tSet path + size:",set_path)
			print("\tDetected size:"+str(cmpsize))

		# Find files with matching texture size and setpath
		# structure of matching:
		#		if listed file exists (failsafe, always should be via listdir)
		#		if the basename match the setname (with size chopped off)
		#		if the below match pattern exists (e.g. if unrelated files in folder, skip)
		#		if the size param, e.g. 2K matches, via comparing the STRING number
		#		OR if the size value is HIRES
		set_files = [file for file in os.listdir(dirname)
					if (os.path.isfile(os.path.join(dirname,file))
					and os.path.basename(file).startswith(set_presize)
					and ((re.search(SEARCH_SIZE,os.path.basename(file)) is not None
						and re.search(SEARCH_SIZE,os.path.basename(file)
						).group(0)[1:-1]==cmpsize))
						or (re.search(SEARCH_HIRES,os.path.basename(file)) is not None
						and cmpsize=="HIRES"
						))]

		# pre-determine the workflow method, greedy towards METALNESS
		# but fallback to DIELECTRIC, unless only specular exists
		neutral_count = 0
		specular_count = 0

		for file in set_files:
			bf = os.path.basename(file)
			if "metalness" in bf.lower():
				# Don't need full regex for workflow metalness detection
				self.workflow = "METALNESS"
				break
			m = re.search(SPEC_WORKFLOW, bf)
			if not m:
				neutral_count += 1
			else:
				specular_count += 1
		if self.workflow!="METALNESS":
			if specular_count>0 and neutral_count==0:
				self.workflow = "SPECULAR"
				self.status["Specular workflow found"] = \
						["Download metalness workflow files instead"]
			else:
				self.workflow = "DIELECTRIC" # default, most common case

		if verbose:
			print("\tDetected workflow: {}".format(
					str(self.workflow)))
			print("\tMaterial files:")
			print("\t", set_files)

		# go file by file, matching passes where possible and matching workflow
		# Matching is greedy: assign first, and then re-assign if more fitting
		# match exists (e.g. when preferring VAR1 over VAR2)
		for file in sorted(set_files):
			matched_to_pass = False
			bf = os.path.basename(file)

			# match passes to loose pass names, e.g. COLOR and COL will both match
			for passtype in self.get_passes_loose_names():

				# skip invalid apss names
				if not hasattr(self.passes, passtype.upper()):
					# shouldn't really ever occur
					continue

				# pre-determined includes or excludes
				if not self.use_ao and passtype == "AO":
					continue
				if not self.use_disp and passtype in ["DISPLACEMENT", "DISP"]:
					continue
				if not self.use_bump and passtype == "BUMP":
					continue

				# do check for 16-bit variant
				# greedy include, pass if non 16-bit already set AND setting is off
				src = re.search(r"(?i)[-_ ]{1}"+passtype+r"[-_ ]{1}",bf)
				if not src:
					src_16 = re.search(r"(?i)[-_ ]{1}"+passtype+r"16[-_ ]{1}",bf)
					if not src_16:
						# print("Pass skip, not in filename: "+passtype)
						continue
					elif getattr(self.passes, passtype.upper()) != None and \
							not self.use_sixteenbit:
						continue # ie pass already exists and 16bit not enabled

				# check matchingness to workflow type
				if self.workflow=="METALNESS" and re.search(SPEC_WORKFLOW, bf):
					if verbose:
						print("\tSkipping file, not metal workflow: ",bf)
					continue # skip any specular matches
				elif self.workflow=="SPECULAR" and re.search(METAL_WORKFLOW, bf):
					if verbose:
						print("\tSkipping file, not specular workflow: ",bf)
					continue
				elif passtype == "METALNESS" and \
						passtype not in re.sub(METAL_WORKFLOW, "", bf):
					if verbose:
						print("\tSkipping file, metalness is for workflow not pass: ",bf)
					continue # ie was matching metalness against workflow, not passname

				# scenario where 16 bit enabled, and already has filled pass slot
				# should choose to skip this non-16 bit pass (since src is ! None)
				if self.use_sixteenbit and src:
					if getattr(self.passes, passtype.upper()) is not None:
						continue

				# Prefer lowest var number, if there are any
				varn = re.search(SEARCH_VAR,bf)
				if varn:
					present_pass = getattr(self.passes, passtype.upper())
					if present_pass != None:
						varn_current = re.search(SEARCH_VAR,bf)
						varnint_current = int(varn_current.group(0)[4:-1])
						varnint = int(varn.group(0)[4:-1])
						if varnint_current >= varnint:
							continue

				matched_to_pass = True
				# set path to that pass' file,
				# e.g. self.passes.AO = '/path/to/setname_AO.jpg'
				setattr(self.passes, passtype.upper(), os.path.join(dirname,file))

				# do size check from filename, looking for e.g. 2K
				m = re.search(SEARCH_SIZE,bf)
				hi = re.search(SEARCH_HIRES,bf)
				if m:
					tmpsize = int(m.group(0)[1:-2]) # cut off the _ & k_
					if self.size==None:
						self.size = m.group(0)[1:-1]
					else:
						if tmpsize < int(self.size[:-1]):
							self.size = m.group(0)[1:-1]
				elif hi:
					if self.size==None:
						self.size = hi.group(0)[1:]

			if matched_to_pass is False and verbose:
				print("\tFile not matched to pass type: "+file)

		# Identify critical passes and what should create warnings/not auto
		# check for importing because such image pass is missing
		missing_critical = []
		if self.workflow=="METALNESS":
			if not self.passes.COLOR and not self.passes.ALPHAMASKED:
				missing_critical.append("Color")
			if not self.passes.METALNESS: missing_critical.append("Metalness")
			if not self.passes.NORMAL: missing_critical.append("Normal")
			if not self.passes.ROUGHNESS: missing_critical.append("Roughness")
		else:
			if not self.passes.COLOR and not self.passes.ALPHAMASKED:
				missing_critical.append("Color")
			# if not self.passes.REFLECTION: missing_critical.append("Reflection")
			if not self.passes.GLOSS: missing_critical.append("Gloss")
			if not self.passes.NORMAL: missing_critical.append("Normal")

		# generate associated warnings
		if len(missing_critical)>0:
			self.status["Missing critical passes"]=[str(missing_critical)]
			if self.verbose:
				print("Poliigon: Missing critical passes: ",missing_critical)

		if not dryrun:
			self.build_material(context, files=set_files)
			self.save_settings_to_props() # save workflow settings to material

		return self.status, self.material

	def build_name(self):
		"""Default name for the material being generated"""
		if self.mapping == 'box_standard':
			return str(self.setname) + "_box"
		if self.mapping == 'box_object':
			return str(self.setname) + "_box_obj"
		return str(self.setname)

	def build_material(self, context, files=[], workflow=None, material=None):
		"""Generic function to create material from provided data"""
		if self.verbose:
			print("Poliigon: Building material")

		# load variables if provided
		if workflow != None:
			self.workflow = workflow

		if self.engine is None:
			self.status["ERROR"] = ["Workflow not yet set"]
			return

		mat_config = self.load_nodegroup_config(self.engine)
		if not mat_config:
			self.status["ERROR"] = ["Workflow could not be imported for",
									"engine "+self.engine]
			return

		# create new or check if material exists
		if material is None:
			self.material = bpy.data.materials.new(self.build_name())
		else:
			if material not in bpy.data.materials:
				return {"ERROR", "Material does not exist"}
			self.material = material

		# will also mutate the mat_config with node references
		node_group = self.create_nodegroup_from_config(mat_config)

		# creates the mapping nodes etc, cycles specific: returns special nodes
		special = self.setup_material_from_nodegroup(mat_config, node_group)

		# created named ID property, for material panel manipulation ui
		special["mapping"]["main_map"] = True

		# engine agnosticly update images
		for imgpass in self.get_passes():
			self.load_images_into_material(mat_config, imgpass)

		# update the color settings (might be cycles specific)
		self.update_image_node_colorsettings(mat_config)

		# conform UV mapping, run after loading images
		if self.conform_uv:
			self.conform_uv_mapping(mat_config, special["mapping"])

		# additional rules/logic post base creation
		self.update_cycles_principled(context, mat_config, node_group)

		# cleanup unused reroutes
		self.reroute_cleanup(node_group)

		# load the principled mixer shader for convinience
		self.create_principled_mixer()

	def setup_material_from_nodegroup(self, mat_config, node_group):
		"""Create a generic material with a given nodegroup

		To support multiple engines in future, fork this function as needed.
		"""

		# general settings
		self.material.use_fake_user = True
		self.material.use_nodes = True

		# if a carpet node, use a principled sheen settings
		is_rug = self.is_rug_name(self.material.name)

		m_nodes = self.material.node_tree.nodes
		m_links = self.material.node_tree.links

		# clear existing nodes (if any), and add new ones
		for node in m_nodes:
			m_nodes.remove(node)

		tex_coords = m_nodes.new(type='ShaderNodeTexCoord')
		material_group = m_nodes.new(type='ShaderNodeGroup')
		principled = m_nodes.new(type='ShaderNodeBsdfPrincipled')
		if bpy.app.version >= (2, 80):
			disp = m_nodes.new(type='ShaderNodeDisplacement') # 2.8
		else:
			# TODO: determine way to use displacement back in 2.7 consistently
			pass

		output = m_nodes.new(type='ShaderNodeOutputMaterial')

		if self.mapping == 'uv_simple_mapping':
			mapping = m_nodes.new(type='ShaderNodeGroup')
			mapping_group = self.get_simple_mapping_group()

			# custom_mapping
			mapping.node_tree = mapping_group
			mapping.name = mapping_group.name
		elif self.mapping == 'uv_mosaic_mapping':
			mapping = m_nodes.new(type='ShaderNodeGroup')
			mapping_group = self.get_mosaic_mapping_group()

			# custom_mapping
			mapping.node_tree = mapping_group
			mapping.name = mapping_group.name
		else:
			mapping = m_nodes.new(type='ShaderNodeMapping')
		material_group.node_tree = node_group
		material_group.name = node_group.name

		# set location
		tex_coords.location[0] -= 700
		mapping.location[0] -= 500
		mapping.width = 200
		material_group.location[0] -= 250
		material_group.width = 225
		principled.location[0] += 100 + 200
		principled.location[1] += 200
		if bpy.app.version >= (2, 80):
			disp.location[0] += 100 + 200
			disp.location[1] -= 400
		output.location[0] += 600 + 200
		output.location[1] += 200

		# create links
		if self.mapping in ('uv_simple_mapping', 'uv_mosaic_mapping'):
			m_links.new(
				tex_coords.outputs["UV"],
				mapping.inputs["UV"])
			m_links.new(
				mapping.outputs["UV"],
				material_group.inputs["Vector"])
		elif self.mapping == 'uv_standard':
			m_links.new(
				tex_coords.outputs["UV"],
				mapping.inputs["Vector"])
			m_links.new(
				mapping.outputs["Vector"],
				material_group.inputs["Vector"])
		elif self.mapping in ('box_standard'):
			m_links.new(
				tex_coords.outputs["Generated"],
				mapping.inputs["Vector"])
			m_links.new(
				mapping.outputs["Vector"],
				material_group.inputs["Vector"])
		elif self.mapping == 'box_object':
			m_links.new(
				tex_coords.outputs["Object"],
				mapping.inputs["Vector"])
			m_links.new(
				mapping.outputs["Vector"],
				material_group.inputs["Vector"])
		else:
			if self.verbose:
				print("Warning: no valid selection for mapping type")

		m_links.new(
			material_group.outputs["Base Color"],
			principled.inputs["Base Color"])

		if self.passes.SSS:
			m_links.new(
				material_group.outputs["SSS Color"],
				principled.inputs["Subsurface Color"])
			principled.inputs["Subsurface"].default_value = 0.02
		else:
			principled.inputs["Subsurface"].default_value = 0
			node_group.outputs.remove(node_group.outputs["SSS Color"])

		if self.passes.METALNESS:
			m_links.new(
				material_group.outputs["Metallic"],
				principled.inputs["Metallic"])
		else:
			node_group.outputs.remove(node_group.outputs["Metallic"])

		if self.passes.ROUGHNESS or self.passes.GLOSS:
			m_links.new(
				material_group.outputs["Roughness"],
				principled.inputs["Roughness"])
		else:
			node_group.outputs.remove(node_group.outputs["Roughness"])

		if self.passes.TRANSMISSION:
			m_links.new(
				material_group.outputs["Transmission"],
				principled.inputs["Transmission"])
		else:
			node_group.outputs.remove(node_group.outputs["Transmission"])

		if self.passes.NORMAL:
			m_links.new(
				material_group.outputs["Normal"],
				principled.inputs["Normal"])
		else:
			node_group.outputs.remove(node_group.outputs["Normal"])

		if not self.passes.AO:
			node_group.inputs.remove(node_group.inputs["AO Strength"])

		if not self.passes.BUMP:
			node_group.inputs.remove(node_group.inputs["Bump Strength (distance)"])

		# Micro displacement does not work with normal and displacement maps at
		# the same time, so disable normal (if dispalcement used), and set the
		# displacement default to 0.05.
		if not self.microdisp:
			pass
		elif self.passes.DISPLACEMENT:
			# With Displacement: Normal Strength=0, Bump Distance=0.02,
			# Displacement Strength=0.05 (no longer to be 0)
			material_group.inputs["Displacement Strength"].default_value = 0.05
			if self.passes.NORMAL:
				material_group.inputs["Normal Strength"].default_value = 0
				print("Setting Normal strength to zero, given non-zero displacement")

		m_links.new(
			principled.outputs["BSDF"],
			output.inputs["Surface"])
		if bpy.app.version > (2, 80):
			# Alpha socket only avail. in 2.8+
			if self.passes.ALPHA or self.passes.ALPHAMASKED:
				m_links.new(
					material_group.outputs["Alpha"],
					principled.inputs["Alpha"])
			else:
				node_group.outputs.remove(node_group.outputs["Alpha"])

			# different displacement approach for 2.8+
			if self.passes.DISPLACEMENT:
				m_links.new(
					material_group.outputs["Displacement"],
					disp.inputs["Height"])
				m_links.new(
					disp.outputs["Displacement"],
					output.inputs["Displacement"])
				disp.inputs["Midlevel"].default_value = 0.5
				disp.inputs["Scale"].default_value = 1.0

				# Change default node settings
				node_group.outputs
			else:
				node_group.outputs.remove(node_group.outputs["Displacement"])
				node_group.inputs.remove(node_group.inputs["Displacement Strength"])
				node_group.inputs.remove(node_group.inputs["Displacement Mid-Level"])
				m_nodes.remove(disp)

		else:
			if self.verbose:
				print('TODO: Displacement for 2.7x')
			# TODO: Check this if needed, previously just had the 27 version
			# if blender_27:
			# 	disp.space = 'OBJECT_SPACE'
			# else:
			# 	disp.space = 'OBJECT'

		# create transparent mix shader if pre-2.8
		if bpy.app.version < (2, 80):
			if not (self.passes.ALPHA or self.passes.ALPHAMASKED):
				node_group.outputs.remove(node_group.outputs["Alpha"])
			else:
				mix_shader = m_nodes.new(type='ShaderNodeMixShader')
				transparent = m_nodes.new(type='ShaderNodeBsdfTransparent')
				transparent.location[0] += 100 + 200
				transparent.location[1] += 400
				mix_shader.location[0] += 400 + 200
				mix_shader.location[1] += 200
				# output.location[0] += 200 # move material output ove rmore
				m_links.new(
					material_group.outputs["Alpha"],
					mix_shader.inputs[0])
				m_links.new(
					transparent.outputs["BSDF"],
					mix_shader.inputs[1])
				m_links.new(
					principled.outputs["BSDF"],
					mix_shader.inputs[2])
				m_links.new(
					mix_shader.outputs[0],
					output.inputs["Surface"])

		if is_rug:
			principled.inputs["Sheen"].default_value = 1
			principled.inputs["Sheen Tint"].default_value = 0.5 # default

		# Clear the human skin-tinted SSS radius
		principled.inputs["Subsurface Radius"].default_value = [1, 1, 1]

		return {"mapping": mapping}

	def load_images_into_material(self, mat_config, imgpass):
		"""Load available images, engine agnostic"""
		imgpath = getattr(self.passes, imgpass)
		if imgpass not in mat_config["nodes"]:
			if imgpass=="ALPHAMASKED" and imgpath != None:
				image = bpy.data.images.load(imgpath)
				image.name = os.path.basename(imgpath)
				mat_config["nodes"]["COLOR"]["datablock"].image = image
				mat_config["nodes"]["COLOR"]["datablock"].mute = False

			# Pass name MUST match name of an image node,
			# but have it fail silently. This would only
			# ever be an addon configuration error, not user.
			# raise ValueError("Missing node for image pass "+imgpass)
			elif self.verbose:
				print("\tImage node {} not present in material".format(imgpass))
		elif imgpath is None:
			if mat_config["nodes"][imgpass]["datablock"].image:
				print("\tImage pass {} not set, but node already assigned".format(
					imgpass))
				return
			if self.verbose:
				print("\tImage pass {} not set".format(imgpass))
			mat_config["nodes"][imgpass]["datablock"].mute = True
		else:
			# prefer alphamasked over color
			if imgpass=="COLOR" and \
				mat_config["nodes"]["COLOR"]["datablock"].image!=None: return
			if imgpass=="MASK" and \
				mat_config["nodes"]["ALPHA"]["datablock"].image!=None: return
			# prefer alpha over mask
			image = bpy.data.images.load(imgpath)
			image.name = os.path.basename(imgpath)
			mat_config["nodes"][imgpass]["datablock"].image = image
			mat_config["nodes"][imgpass]["datablock"].mute = False # in case overrwite

		# update the mapping, if applicable
		if imgpass in mat_config["nodes"] and self.mapping in ('box_standard', 'box_object'):
			mat_config["nodes"][imgpass]["datablock"].projection = "BOX"
			mat_config["nodes"][imgpass]["datablock"].projection_blend = 0.3

	def update_image_node_colorsettings(self, mat_config):
		"""Update color settings after images are loaded to support 2.7 and 2.8"""

		# cache nodes for applying color space, as with later 2.8 builds we
		# can only do this after the image has been assigned to the node
		apply_colorspaces = []
		for node_name, node_data in mat_config["nodes"].items():
			if not mat_config["nodes"].get(node_name):
				continue
			if not mat_config["nodes"][node_name]["datablock"]:
				continue
			node = mat_config["nodes"][node_name]["datablock"]
			for key, value in node_data.items():
				if key != 'color_space':
					continue
				apply_colorspaces.append([node, value])

		# now apply the updated color settings
		for node, color_set in apply_colorspaces:
			if hasattr(node, 'color_space'): # 2.7x
				node.color_space = 'NONE' if color_set == 'Non-Color' else 'COLOR'
			elif node.image and hasattr(node.image, 'colorspace_settings'): # 2.8x
				if color_set == 'NONE':
					color_set = 'Non-Color'
				elif color_set == 'COLOR':
					color_set = 'sRGB'
				try:
					node.image.colorspace_settings.name = color_set
				except:
					if color_set == 'Non-Color':
						node.image.colorspace_settings.name = 'Linear'
					else:
						raise Exception("Failed to update colorspace setting")
			else:
				if self.verbose:
					print("Could not apply {} color to node {}; image {}".format(
						color_set, node, node.image))

	def conform_uv_mapping(self, mat_config, mappping_node):
		"""Update the mapping node x-scale to fit the image aspect ratio"""

		# Get aspect ratio from color image (fallback to normal, if missing)
		img = mat_config["nodes"]["COLOR"]["datablock"].image
		if img is None:
			img = mat_config["nodes"]["NORMAL"]["datablock"].image

		if img and img.size[0] > 0 and img.size[1] > 0:
			ratio = img.size[0]/img.size[1]  # width / height
			if self.mapping in ('uv_simple_mapping', 'uv_mosaic_mapping'):
				mappping_node.inputs[2].default_value = ratio
			else:
				if hasattr(mappping_node, 'scale'):
					mappping_node.scale[0] = 1/ratio
				else:
					mappping_node.inputs['Scale'].default_value[0] = 1/ratio
		else:
			if self.verbose:
				print("Poliigon: No color/normal image, couldn't conform to UV")

	def update_cycles_principled(self, context, mat_config, new_group):
		"""Update shader designed for Blender Cycles Principled Shader"""

		# setup and build material
		ng_nodes = new_group.nodes
		ng_links = new_group.links

		# parent full material node tree
		mat_tree = self.material.node_tree

		# get the principled node in a stable way invariant to generated name
		principled = None
		for node in mat_tree.nodes:
			if node.type != 'BSDF_PRINCIPLED':
				continue
			principled = node
			break
		if principled is None:
			raise Exception('Could not extract principled node for updating')

		# disable sample as light to reduce noise
		if hasattr(self.material, "cycles"):
			self.material.cycles.sample_as_light = False

		if self.passes.COLOR or self.passes.ALPHAMASKED:
			# Ensure diffuse texture shown in solid-with-texture mode, must be
			# the active node to work
			new_group.nodes.active = mat_config["nodes"]["COLOR"]["datablock"]

		# if SSS is present, assign low color value, otherwise delete
		if self.passes.SSS is None:
			ng_nodes.remove(mat_config["nodes"]["SSS"]["datablock"])
			principled.inputs[1].default_value = 0
		else:
			principled.inputs[1].default_value = 0.005
			# mat_config["nodes"]["Group Output"]["datablock"].inputs[1].default_value = 0.005
			# mat_config["nodes"]["Principled BSDF"]["datablock"].inputs[1].default_value = 0.005

		if self.workflow == "METALNESS":
			# no reflection or gloss, reconnect roughness to Principled rough
			# ng_nodes.remove(mat_config["nodes"]["REFLECTION"]["datablock"])
			# ng_nodes.remove(mat_config["nodes"]["ReflMultiply"]["datablock"])
			# ng_nodes.remove(mat_config["nodes"]["InvertRefl"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["GLOSS"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["InvertGloss"]["datablock"])

			# make link from roughness node to roughness socket
			rough_node = mat_config["nodes"]["ROUGHNESS"]["datablock"]
			reroute_rough = mat_config["nodes"]["Reroute.ROUGH"]["datablock"]
			ng_links.new(rough_node.outputs[0], reroute_rough.inputs[0])

		elif self.workflow == "SPECULAR" or self.workflow == "DIELECTRIC":
			metal_node = mat_config["nodes"]["METALNESS"]["datablock"]
			ng_nodes.remove(metal_node)
			rough_node = mat_config["nodes"]["ROUGHNESS"]["datablock"]
			ng_nodes.remove(rough_node)

		is_eevee = context.scene.render.engine == 'BLENDER_EEVEE'
		if is_eevee and (self.passes.ALPHA or self.passes.ALPHAMASKED):
			self.material.blend_method = 'CLIP'
			self.material.shadow_method = 'CLIP'

		if self.passes.ALPHAMASKED is not None:
			pass # ALPHA node already deleted
		elif self.passes.ALPHA is None:
			ng_nodes.remove(mat_config["nodes"]["ALPHA"]["datablock"])
		elif self.passes.ALPHA:
			reroute_alpha = mat_config["nodes"]["Reroute.Alpha"]["datablock"]
			alpha = mat_config["nodes"]["ALPHA"]["datablock"]
			ng_links.new(alpha.outputs[0], reroute_alpha.inputs[0])
			reroute_alpha.location[1] -= 150 # move down, to level w/ Alpha

		if self.passes.TRANSMISSION is None:
			ng_nodes.remove(mat_config["nodes"]["TRANSMISSION"]["datablock"])

		# if (hasattr(context.scene, "cycles")
		# 		and hasattr(context.scene.cycles, "feature_set")
		# 		and	context.scene.cycles.feature_set == 'EXPERIMENTAL'):
		# 	try:
		# 		self.material.cycles.displacement_method = 'TRUE'
		# 	except:
		# 		print("Poliigon: Failed to set displacement method to TRUE, continuing")

		if self.passes.AO is None:
			ng_nodes.remove(mat_config["nodes"]["AO"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["AO + COLOR (Multiply)"]["datablock"])
			# re-create the appropriate link
			col = mat_config["nodes"]["Reroute.AO_MULT"]["datablock"]
			color_adjust = mat_config["nodes"]["Reroute.color_adj_input"]["datablock"]
			ng_links.new(col.outputs[0], color_adjust.inputs[0])

		if self.passes.BUMP is None:
			rm = ["BUMP", "reroute.Bump1", "reroute.Bump2", "reroute.Bump3", "BumpMap"]
			for bumpnode in rm:
				ng_nodes.remove(mat_config["nodes"][bumpnode]["datablock"])
			norm = mat_config["nodes"]["Normal Map"]["datablock"]
			norm_reroute = mat_config["nodes"]["Reroute.normal"]["datablock"]
			ng_links.new(norm.outputs[0], norm_reroute.inputs[0])

		if self.passes.DISPLACEMENT is None:
			ng_nodes.remove(mat_config["nodes"]["DISPLACEMENT"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["DISPLACEMENT Adjust"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["DISPLACEMENT Height"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["Disp Fix"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["Disp Fix Invert"]["datablock"])
			ng_nodes.remove(mat_config["nodes"]["Disp Fix Mult"]["datablock"])

			# norm = mat_config["nodes"]["Normal Map"]["datablock"]
			# princ_node = mat_config["nodes"]["Principled BSDF"]["datablock"]
			# ng_links.new(norm.outputs[0], princ_node.inputs["Normal"])
			# if mat_config["nodes"]["Micro Displacement"]["datablock"]:
			# 	ng_nodes.remove(mat_config["nodes"]["Micro Displacement"]["datablock"])
		elif (self.microdisp is True
				and hasattr(self.material, "cycles")
				and hasattr(self.material.cycles, "displacement_method")
				and bpy.app.version >= (2, 80)):
			# self.material.cycles.displacement_method = 'TRUE'
			context.scene.cycles.feature_set = 'EXPERIMENTAL'
			self.material.cycles.displacement_method = 'BOTH'
			self.material.pmc_matprops.use_micro_displacements = True

		# 	disp_tex = mat_config["nodes"]["DISPLACEMENT"]["datablock"]
		# 	displ = mat_config["nodes"]["Micro Displacement"]["datablock"]
		# 	out = mat_config["nodes"]["Material Output"]["datablock"]

		# 	ng_nodes.remove(mat_config["nodes"]["Bump"]["datablock"])
		# 	ng_links.new(disp_tex.outputs[0], displ.inputs[0])
		# 	ng_links.new(displ.outputs[0], out.inputs[2])

		# 	# also reconnect the normal to princ directly
		# 	princ_node = mat_config["nodes"]["Principled BSDF"]["datablock"]
		# 	norm = mat_config["nodes"]["Normal Map"]["datablock"]
		# 	ng_links.new(norm.outputs[0], princ_node.inputs["Normal"])

		# else:
		# 	if mat_config["nodes"]["Micro Displacement"]["datablock"]:
		# 		ng_nodes.remove(mat_config["nodes"]["Micro Displacement"]["datablock"])
			# context.scene.cycles.feature_set = 'EXPERIMENTAL'

			# mute normal nodes, due to not being able to use both at once
			# note! This was only true for Blender 2.7x due to bug
			# nrm = mat_config["nodes"]["NORMAL"]["datablock"]
			# nrmmap = mat_config["nodes"]["Normal Map"]["datablock"]
			# nrm.mute=True
			# nrmmap.mute=True
		elif bpy.app.version >= (2, 80):
			# always set if 2.8
			if hasattr(self.material, "cycles"):
				self.material.cycles.displacement_method = 'BOTH'


	@staticmethod
	def set_material_color_from_image(material, image):
		"""Go through pixels and get an average color to use in viewport"""

		# Currently unused
		# Make the solid view material color inherit from COL image
		# via taking sampled-pixel average of rgb channels
		# NOTE! Even with sampling, this does add (significant) processing
		# time/memory. Possibility to do processing in background thread and
		# assign back to the loaded materials (or in pre-loading state)

		if not image:
			return
		# import time
		# t0=time.time()

		pxlen = len(image.pixels)
		channels = pxlen/image.size[0]/image.size[1] # e.g. 3 or 4
		sampling = pxlen/channels/1024 # number of skips, at most 1024 samples
		if sampling<1:
			sampling=1 # less than 1024 pxls, so full sample/no skips
		skp = int(channels*sampling)

		# critical path, very slow (can't do slices on pixels directly)
		# also duplicates in memory
		lst = list(image.pixels)

		material.diffuse_color[0] = sum(lst[0::skp])/len(lst[0::skp]) # r
		material.diffuse_color[1] = sum(lst[1::skp])/len(lst[1::skp]) # g
		material.diffuse_color[2] = sum(lst[2::skp])/len(lst[2::skp]) # b

		# feabile attempt to tell python to release memory back sooner
		del lst
		#print(">> COLOR PROCESS TIME IS: ",time.time()-t0)

	@staticmethod
	def load_nodegroup_config(engine_template):
		"""Load in json node config for material based on set engine"""

		jsonfile = os.path.join(
			os.path.dirname(__file__), "engines", engine_template + ".json")
		if not os.path.isfile(jsonfile):
			print("Missing json file for workflow "+engine_template)
			raise Exception("Missing json file for workflow")
		with open(jsonfile) as jsonread:
			mat_config = json.load(jsonread)
		# mat_config = {}

		# convert certain things,
		# e.g., convert all locations to mathutils.vector(value)
		# and turn the lists in the default values into sets/tuples

		return mat_config

	def create_nodegroup_from_config(self, mat_config):
		"""Given a dictionary json object, create a node group"""
		nodegroup = bpy.data.node_groups.new(
			self.material.name, type='ShaderNodeTree')
		m_nodes = nodegroup.nodes
		m_links = nodegroup.links

		# cache nodes for applying color space, as with later 2.8 builds we
		# can only do this after the image has been assigned to the node
		apply_colorspaces = []

		frames_with_children = []

		for node_name, node_data in mat_config["nodes"].items():
			if not hasattr(bpy.types, node_data["type_id"]):
				if self.verbose:
					print("Node not available here")
				mat_config["nodes"][node_name]["datablock"] = None
				continue
			node = m_nodes.new(node_data["type_id"])
			node.select = False
			mat_config["nodes"][node_name]["datablock"] = node
			node.name = node_name
			if 'reroute' not in node_name.lower():
				node.label = mat_config["nodes"][node_name]['label']
			for key, value in node_data.items():
				if key in {"type", "type_id", "datablock", "COMMENT_ONLY"}:
					continue
				if hasattr(value, '__call__'):
					value = value()

				if key=='color_space':
					# special apply cases, to support newer 2.8 builds
					apply_colorspaces.append([node, value])
				elif key=='parent':
					frames_with_children.append(value)
					# apply parent (frame) to node if any
					# setattr(node, key, mat_config["nodes"][value]["datablock"])
					pass # TODO, get this working in 2.7
				elif key=='text':
					if node.name not in bpy.data.texts:
						txtblock = bpy.data.texts.new(node.name)
						txtblock.write(value)
					else:
						txtblock = bpy.data.texts[node.name]
					node.text = txtblock
				else: # general case
					setattr(node, key, value)

			# TODO: remove if 2.8 special spacing no longer needed
			# # fix 2.8 node spacing
			# if bpy.app.version >= (2, 80):
			# 	# image nodes are wider now, move farther left
			# 	if node.location[0] <= -430:
			# 		node.location[0] -= 200
			# 	if node_name == "Principled BSDF":
			# 		node.location[1] += 50
			# 	#node.location[0] *= 1.2 # space out nodes some more

		# Apply the parents for nodes, now that all nodes exist
		for node_name, node_data in mat_config["nodes"].items():
			for key, value in node_data.items():
				node = mat_config["nodes"][node_name]["datablock"]
				if node is None:
					errstr = ("Could not load node {}, likely not available "
						"in this version of blender")
					raise RuntimeError(errstr.format(node_name))
				if key != 'parent':
					continue
				# apply parent (frame) to node if any
				try:
					setattr(node, key, mat_config["nodes"][value]["datablock"])
				except:
					print("For name/node/key/:", node_name, node, key, value)
					print("Node likely unavailable in this blender version: "+node_name)
					raise

		# Repeat-apply location for frames
		for node_name, node_data in mat_config["nodes"].items():
			node = mat_config["nodes"][node_name]["datablock"]
			if node.type != 'FRAME':
				continue
			elif node_name in frames_with_children:
				# double coordinates for frames with children to show up right
				node.location = [node_data['location'][0]*2, node_data['location'][1]*2]
			else:
				node.location = [node_data['location'][0], node_data['location'][1]]

		# Create the group input and output sockets
		for i, socket in enumerate(mat_config["inputs"]):
			nodegroup.inputs.new(
				self.socket_type_to_class(socket['type']), socket['name'])
			if 'min' in socket:
				nodegroup.inputs[i].min_value = socket['min']
			if 'max' in socket:
				nodegroup.inputs[i].max_value = socket['max']
			nodegroup.inputs[i].default_value = socket['default']
		for i, socket in enumerate(mat_config["outputs"]):
			nodegroup.outputs.new(
				self.socket_type_to_class(socket['type']), socket['name'])
			if 'min' in socket:
				nodegroup.outputs[i].min_value = socket['min']
			if 'max' in socket:
				nodegroup.outputs[i].max_value = socket['max']
			nodegroup.outputs[i].default_value = socket['default']

		if "COLOR" in mat_config and mat_config["nodes"]["COLOR"]["datablock"]:
			# To set the diffuse color texture preview in cycles texture mode
			mat_config["nodes"]["COLOR"]["datablock"].select = True
			m_nodes.active = mat_config["nodes"]["COLOR"]["datablock"]

		# Linking
		for lnk in mat_config["links"]:
			from_node = lnk['from']
			from_socket = lnk['from_socket']
			to_node = lnk['to']
			to_socket = lnk['to_socket']

			if not mat_config["nodes"][from_node] or not mat_config["nodes"][to_node]:
				continue

			# resolve the to_socket and from_socket to *index* (not name) input
			# based on original key of '_socket.identifier' (uniquely named)
			from_index = self.socket_index_from_identifier(
				mat_config["nodes"][from_node]["datablock"],
				from_socket, lnk['from_id'], 'from')
			to_index = self.socket_index_from_identifier(
				mat_config["nodes"][to_node]["datablock"],
				to_socket, lnk['to_id'], 'to')

			if from_index is None or to_index is None:
				if self.verbose:
					print("Skipping link, could not fetch index")
				continue

			m_links.new(
				# mat_config["nodes"][from_node]["datablock"].outputs[from_socket],
				# mat_config["nodes"][to_node]["datablock"].inputs[to_socket])
				mat_config["nodes"][from_node]["datablock"].outputs[from_index],
				mat_config["nodes"][to_node]["datablock"].inputs[to_index])

		# updating defaults
		for d_set in mat_config["defaults"]:
			node = d_set['node']
			socket = d_set['socket']
			value = d_set['value']

			socket_id = self.socket_index_from_identifier(
				mat_config["nodes"][node]["datablock"],
				d_set['socket'], d_set['socket_id'], 'to')

			try:
				mat_config["nodes"][node]["datablock"].inputs[socket_id].default_value = value
			except Exception as err:
				print("Poliigon: Error setting default node value: ", node, socket, socket_id, value, str(err))

		return nodegroup

	@staticmethod
	def socket_type_to_class(type_id):
		"""Mapping of input types to class strings"""
		if type_id == 'RGBA': #??
			return 'NodeSocketColor'
		elif type_id == 'VALUE':
			return 'NodeSocketFloat'
		elif type_id == 'VECTOR':
			return 'NodeSocketVector'
		elif type_id == 'CUSTOM':
			print("WARNING! Mapping custom socket tupe to float")
			return 'NodeSocketFloat'
		else:
			raise Exception('Unknown node socket type: '+type_id)

	@staticmethod
	def socket_index_from_identifier(node, name, identifier, mode):
		"""Get the input or output socket index based on identifier name"""
		res = None

		# short circuit return for routes, as the identifier doesn't match well
		# (ie, identifier="output", but actual index available is "Output")
		if node.type == "REROUTE":
			return 0 # in either case, to or from

		if mode == 'from':
			iterset = node.outputs
		elif mode == 'to':
			iterset = node.inputs
		else:
			raise Exception('Invalid mode for socket identifier')

		# ignore empty string names... e.g. in principled shader
		sockets = [sock.name for sock in iterset if sock.name]

		if len(sockets) == len(set(sockets)):
			# all values are unique, we can use the Socket name directly
			res = name
		else:
			# print("Names not unique in: ", sockets)
			# Names not unique, fallback to using the identifier
			# this happens for instance with Math nodes.
			for i, socket in enumerate(iterset):
				if socket.identifier == identifier:
					res = i
					break

		if res is None:
			print('Could not determine node socket from input:')
			print('Node: {}, identifier: {}, mode: {}'.format(
				node, identifier, mode))
			raise Exception('Could not determine node socket from input')
		return res

	def get_mosaic_mapping_group(self):
		"""Returns the group used for mapping based on user selection"""

		if self.mapping_name_mosaic in bpy.data.node_groups:
			return bpy.data.node_groups[self.mapping_name_mosaic]

		# if using uber mapping, use load_nodegroup_config(json path)
		mat_config = self.load_nodegroup_config("mosaic_uv_mapping")
		node_group = self.create_nodegroup_from_config(mat_config)
		node_group.name = self.mapping_name_mosaic

		return node_group

	def get_simple_mapping_group(self):
		"""Returns the group used for mapping based on user selection"""

		if self.mapping_name_simple in bpy.data.node_groups:
			return bpy.data.node_groups[self.mapping_name_simple]

		# if using uber mapping, use load_nodegroup_config(json path)
		mat_config = self.load_nodegroup_config("simple_uv_mapping")
		node_group = self.create_nodegroup_from_config(mat_config)
		node_group.name = self.mapping_name_simple

		return node_group

	@staticmethod
	def reroute_cleanup(node_tree):
		"""Remove unused reroute nodes automatically and recursively"""
		while True:
			local_change = False
			for node in node_tree.nodes:
				if node.type != 'REROUTE':
					continue
				if not node.inputs[0].links or not node.outputs[0].links:
					node_tree.nodes.remove(node)
					local_change = True
			if not local_change:
				break

	def create_principled_mixer(self, force=False):
		"""Creates the principled mixer if it does not exist"""

		if force is False and self.mixer_name in bpy.data.node_groups:
			return bpy.data.node_groups[self.mixer_name]

		mixer = self.load_nodegroup_config("pbr_mixer")
		node_group = self.create_nodegroup_from_config(mixer)
		node_group.name = self.mixer_name

		return node_group

	@staticmethod
	def is_rug_name(name):
		"""Returns true if input name appears to be like a rug name"""
		name = name.lower()
		for itm in RUG_NAMES:
			if itm in name:
				return True
		return False


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------


def get_preferences(context=None):
	"""Multi version compatibility for getting preferences"""
	if not context:
		context = bpy.context
	prefs = None
	if hasattr(context, "user_preferences"):
		prefs = context.user_preferences.addons.get(__package__, None)
	elif hasattr(context, "preferences"):
		prefs = context.preferences.addons.get(__package__, None)
	if prefs:
		return prefs.preferences
	else:
		raise Exception("Could not fetch user preferences")
