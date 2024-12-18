import csv

def get_csv_column_names(file_path):
    """
    Returns the column names of a CSV file at the given path.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        list: List of column names.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or not a valid CSV.
    """
    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            # Read the first row as column names
            try:
                column_names = next(reader)
            except StopIteration:
                raise ValueError("The CSV file is empty")
            
            # Strip any leading/trailing whitespace from column names
            return [name.strip() for name in column_names]
    
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")