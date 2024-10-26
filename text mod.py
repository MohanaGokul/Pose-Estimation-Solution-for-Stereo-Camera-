with open("zed_data.txt", "r") as input_file, open("zed_data_modified.txt", "w") as output_file:
    # Iterate over each line in the original file
    for line in input_file:
        # Remove the first 45 characters from each line and write the rest to the new file
        output_file.write(line[45:])

def mean_of_four_lines(input_file, output_file):
    with open(input_file, 'r') as infile:
        lines = infile.readlines()
        
    means = []
    for i in range(0, len(lines), 4):
        # Get the next four lines (or fewer if at the end)
        chunk = lines[i:i+4]
        
        # Process the lines to compute the mean
        if chunk:
            # Split and convert each line to float
            numbers = [list(map(float, line.strip().split(','))) for line in chunk]
            # Calculate the mean for each position
            mean_values = [sum(x) / len(numbers) for x in zip(*numbers)]
            # Append the formatted mean values to the result
            means.append(', '.join(f"{mean:.2f}" for mean in mean_values))
    
    # Write the means to the output file
    with open(output_file, 'w') as outfile:
        for mean in means:
            outfile.write(mean + '\n')

# Usage
input_filename = 'zed_data_modified.txt'  # Replace with your input file name
output_filename = 'zed_data_mod.txt'  # Replace with your desired output file name
mean_of_four_lines(input_filename, output_filename)

        
