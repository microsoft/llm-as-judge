import importlib
from abc import ABC, abstractmethod


class DataSetAdapter(ABC):
    @abstractmethod
    def load_data(self):
        """
        Load and return the dataset as a numpy array or similar structure.
        
        Returns:
            data (np.ndarray or similar): The feature data for training.
        """
        pass


class ClusteringPlugin:
    """
    A semantic kernel plugin for training and inference with a clustering algorithm.
    
    The algorithm to use is defined as a string (e.g., "KMeans") and is dynamically loaded from
    sklearn.cluster using importlib. Training and inference steps are separated into different functions.
    
    Attributes:
        algorithm_name (str): Name of the clustering algorithm (from sklearn.cluster).
        dataset_connection (DataSetAdapter): An adapter instance to load the dataset.
        model_params (dict): Additional keyword arguments for initializing the clustering model.
        model: The trained clustering model instance.
    """
    
    def __init__(self, algorithm_name: str, dataset_connection: DataSetAdapter, **kwargs):
        """
        Initialize the ClusteringPlugin.
        
        Parameters:
            algorithm_name (str): The name of the clustering algorithm to use (e.g., "KMeans").
            dataset_connection (DataSetAdapter): An instance that implements the DataSetAdapter abstract class.
            **kwargs: Additional parameters to be passed to the clustering algorithm constructor.
        
        Raises:
            ImportError: If the sklearn.cluster module cannot be imported.
            ValueError: If the specified algorithm is not found in sklearn.cluster.
        """
        self.algorithm_name = algorithm_name
        self.dataset_connection = dataset_connection
        self.model_params = kwargs
        self.model = None
        
        # Dynamically import the clustering algorithm from sklearn.cluster using importlib.
        try:
            clustering_module = importlib.import_module("sklearn.cluster")
            self.algorithm_class = getattr(clustering_module, algorithm_name)
        except ImportError as e:
            raise ImportError(f"Could not import sklearn.cluster: {str(e)}")
        except AttributeError:
            raise ValueError(f"Clustering algorithm '{algorithm_name}' not found in sklearn.cluster.")
    
    def train(self):
        """
        Train the clustering model using data loaded from the dataset adapter.
        
        The method loads data, instantiates the clustering algorithm with the provided parameters,
        and fits the model to the data.
        
        Returns:
            model: The trained clustering model.
        """
        # Load the dataset using the provided adapter.
        data = self.dataset_connection.load_data()
        
        # Instantiate the clustering model with the provided parameters.
        self.model = self.algorithm_class(**self.model_params)
        
        # Fit the model to the loaded data.
        self.model.fit(data)
        return self.model
    
    def infer(self, new_data):
        """
        Perform inference using the trained clustering model on new data.
        
        Parameters:
            new_data (array-like): The new data to cluster.
            
        Returns:
            cluster_labels: The cluster labels predicted by the model.
            
        Raises:
            Exception: If the model has not been trained yet.
            NotImplementedError: If the clustering algorithm does not support inference via predict.
        """
        if self.model is None:
            raise Exception("Model has not been trained. Please call the train() method first.")
        
        # Check if the model supports a predict method.
        if hasattr(self.model, 'predict'):
            return self.model.predict(new_data)
        else:
            raise NotImplementedError("The clustering algorithm does not support inference via predict method.")


class CSVDataSetAdapter(DataSetAdapter):
    def __init__(self, file_path, delimiter=","):
        self.file_path = file_path
        self.delimiter = delimiter
    
    def load_data(self):
        """
        Load data from a CSV file into a numpy array.
        
        Returns:
            np.ndarray: The data loaded from the CSV file.
        """
        import pandas as pd
        df = pd.read_csv(self.file_path, delimiter=self.delimiter)
        # Assuming the features are all columns; modify if needed.
        return df.values
