def Mode(arr):
    if arr == []:
        return arr
    else:
        # sort arr
        arr.sort()
        sorted_arr = arr  # extra storage
        # init variables
        values = []
        freq = [1] # freq starts at 1
        first = 0  # first index begins
        values.append(sorted_arr[first])  # add first value
        # creating values and freq arr's
        for i in sorted_arr:
            next = first + 1 # next will be iteration of first
            if next == len(sorted_arr):
                break
            elif sorted_arr[next] != sorted_arr[first]:
                values.append(sorted_arr[next]) # put next number into values arr
                freq.append(1) # add new freq into freq arr
            else:
                if first < len(freq):
                    freq[first] = (freq[first] + 1)  # if numbers are the same,
                    # we will add to the current freq by 1
                else:
                    freq[first-1] = (freq[first-1] + 1)
                    break
            first = next # loop to new spot in sorted arr
           

        # find highest freq in freq arr
        highest = freq[0]
        for i in freq:
            if i > highest:
                highest = i

        # find index of highest num
        index = 0
        for i in freq:
            if freq[index] == highest: # check to see if we've reached the right one
                break
            else:
                index += 1 # otherwise, iterate the index num
        mode = values[index] # now we have the same index of where our mode is in values
        print(mode, "mode")
        return mode

Mode([3, 4, 1, 5, 4])
Mode([4, 6, 6, 3, 3, 1, 2, 3])
