import pandas as pd
import numpy as np
import static_frame as sf
import hashlib, pickle, os
from pathlib import Path
from utils.sorting import get_path

def disk_cache(func):
    def wrapped(*args, **kwargs):
        # Create a unique hash for the arguments
        hash_parts = []
        
        for arg in args:
            if isinstance(arg, sf.Frame):
                # Use StaticFrame to create a hash for DataFrame
                hash_parts.append(arg.via_hashlib(include_name=False).sha256().hexdigest())
            elif isinstance(arg, list):
                # Serialize the list to create a hash
                hash_parts.append(hashlib.sha256(pickle.dumps(arg)).hexdigest())
            elif isinstance(arg, np.ndarray):
                # Use the array's bytes to create a hash
                hash_parts.append(hashlib.sha256(arg.tobytes()).hexdigest())
            elif isinstance(arg, pd.DataFrame):
                raise TypeError("Cannot cache pandas DataFrames, use StaticFrame instead.")
            else:
                # For other types, use their string representation
                hash_parts.append(hashlib.sha256(str(arg).encode()).hexdigest())
        
        # Combine the hashes to create a unique file name
        hash_digest = "_".join(hash_parts)
        os.makedirs(get_path('temp/'), exist_ok=True)
        file_path = Path(get_path('temp/')) / f"{func.__name__}_{hash_digest}"
        
        # Check if the cached file exists
        if file_path.exists():
            # Load the cached result based on its type
            if file_path.suffix == '.npz':
                return np.load(file_path, allow_pickle=True)
            elif file_path.suffix == '.pkl':
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            elif file_path.suffix == '.sf':
                return sf.read(file_path)
        
        # Call the original function and get the result
        result = func(*args, **kwargs)
        
        # Save the result to disk based on its type
        if isinstance(result, sf.Frame):
            result.to_npz(file_path)
        elif isinstance(result, np.ndarray):
            np.save(file_path, result)
        elif isinstance(result, list) or isinstance(result, dict):
            with open(file_path.with_suffix('.pkl'), 'wb') as f:
                pickle.dump(result, f)
        else:
            # For other types, save as text or handle accordingly
            with open(file_path.with_suffix('.txt'), 'w') as f:
                f.write(str(result))
        
        return result
    
    return wrapped
