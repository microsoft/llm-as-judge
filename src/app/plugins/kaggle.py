import os
from typing import Optional

import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi


class KaggleDatasetReader:
    """
    A semantic kernel plugin for reading Kaggle datasets.
    
    This class uses the Kaggle API to download datasets from Kaggle.
    It can return a list of downloaded file names or, if a file is specified,
    read its contents into a pandas DataFrame (for CSV files) or as a text string
    (for other file types).

    Usage Example:
        # Initialize with your Kaggle credentials (or set them in your environment)
        reader = KaggleDatasetReader(kaggle_username="your_username", kaggle_key="your_key")

        # To list all files in a dataset:
        files = reader.read_dataset("zynicide/wine-reviews")
        print(files)

        # To read a specific CSV file from the dataset:
        df = reader.read_dataset("zynicide/wine-reviews", file_name="winemag-data_first150k.csv")
        print(df.head())
    """

    def __init__(self, kaggle_username: Optional[str] = None, kaggle_key: Optional[str] = None):
        """
        Initializes the KaggleDatasetReader.
        
        Parameters:
            kaggle_username (str): Your Kaggle username. If provided, these will be set as environment variables.
            kaggle_key (str): Your Kaggle API key.
            
        If the credentials are not provided, ensure that your Kaggle configuration file
        (~/.kaggle/kaggle.json) is correctly set up.
        """
        if kaggle_username and kaggle_key:
            os.environ['KAGGLE_USERNAME'] = kaggle_username
            os.environ['KAGGLE_KEY'] = kaggle_key
        
        self.api = KaggleApi()
        self.api.authenticate()
        
    def read_dataset(self, dataset: str, file_name: Optional[str] = None, download_path: str = "./kaggle_data", unzip: bool = True):
        """
        Downloads and reads a Kaggle dataset.
        
        This semantic kernel plugin function performs the following:
          1. Downloads the dataset files into a local directory.
          2. If a specific file is provided:
              - Returns a pandas DataFrame if the file is a CSV.
              - Otherwise, returns the file contents as a string.
          3. If no file is provided, returns a list of file names in the downloaded dataset.
        
        Parameters:
            dataset (str): The Kaggle dataset slug (e.g. "zynicide/wine-reviews").
            file_name (str): (Optional) The specific file name to read.
            download_path (str): The local directory where the dataset is downloaded.
            unzip (bool): Whether to unzip the downloaded files.
            
        Returns:
            list or pandas.DataFrame or str:
                - List of file names if `file_name` is None.
                - pandas.DataFrame if `file_name` ends with '.csv'.
                - str for other file types.
                
        Raises:
            FileNotFoundError: If the specified file is not found in the downloaded dataset.
        """
        # Ensure the download path exists
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        # Download dataset files from Kaggle (this will overwrite existing files)
        self.api.dataset_download_files(dataset, path=download_path, unzip=unzip)
        
        # List downloaded files
        files = os.listdir(download_path)
        
        if file_name:
            file_path = os.path.join(download_path, file_name)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File '{file_name}' not found in dataset '{dataset}'.")
            
            # Return a DataFrame if CSV; else, return file contents as text
            if file_path.lower().endswith('.csv'):
                return pd.read_csv(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        
        return files
