import rasterio
import numpy as np
from scipy.optimize import minimize
from bayes_opt import BayesianOptimization
import os

def load_raster(raster_path: str) -> tuple[np.ndarray, rasterio.transform.Affine, rasterio.crs.CRS]:
    """Loads a raster into a NumPy array and returns its metadata."""
    with rasterio.open(raster_path) as src:
        array = src.read(1)
        transform = src.transform
        crs = src.crs
    return array, transform, crs

def write_raster(array: np.ndarray, transform: rasterio.transform.Affine, crs: rasterio.crs.CRS, output_path: str):
    """Writes a NumPy array to a GeoTIFF raster."""
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=array.dtype,
        transform=transform,
        crs=crs,
    ) as dst:
        dst.write(array, 1)

def calculate_rmse(predictions: np.ndarray, reference: np.ndarray) -> float:
    """Calculates the Root Mean Squared Error between two arrays."""
    return np.sqrt(np.mean((predictions - reference) ** 2))

def average_ensemble(prediction_arrays: list[np.ndarray]) -> np.ndarray:
    """Calculates the average ensemble of multiple prediction arrays."""
    return np.mean(np.stack(prediction_arrays), axis=0)

def maximize_rmse(weights: np.ndarray, prediction_arrays: list[np.ndarray], reference_array: np.ndarray) -> float:
    """Calculates the negative RMSE for optimization (since we want to maximize RMSE)."""
    ensemble = np.average(np.stack(prediction_arrays), axis=0, weights=weights)
    return -calculate_rmse(ensemble, reference_array)

def ensemble_prediction(pred_paths: list[str], ref_path: str, 
                        init_points:int=10, n_iter:int=100,
                        avge=True, opte=True):
    """
    init_points=5 n_iter=15 as baselines 
    Calculates and saves the average and optimized (maximizing RMSE) ensemble predictions.

    Args:
        pred_paths (list[str]): List of paths to the prediction raster files.
        ref_path (str): Path to the reference raster file.
        avge (bool, optional): Whether to calculate and save the average ensemble. Defaults to True.
        opte (bool, optional): Whether to calculate and save the optimized ensemble (maximizing RMSE). Defaults to True.

    Returns:
        tuple: A tuple containing the file paths of the average ensemble raster (if avge=True)
               and the optimized ensemble raster (if opte=True). Returns None for either if the
               corresponding argument is False.
    """
    prediction_arrays = []
    for path in pred_paths:
        array, transform, crs = load_raster(path)
        prediction_arrays.append(array)

    reference_array, _, _ = load_raster(ref_path)

    output_dir = os.path.dirname(pred_paths[0])
    avge_fn = None
    opte_fn = None

    if avge:
        avg_ensemble_array = average_ensemble(prediction_arrays)
        avge_fn = os.path.join(output_dir, "AVGe.tif")
        write_raster(avg_ensemble_array, transform, crs, avge_fn)
        print(f"Average ensemble saved to: {avge_fn}")

    if opte:
        num_predictions = len(prediction_arrays)
        print(f'num_predictions @{num_predictions}')

        def bayesian_optimization_function(w1, w2, w3, w4):
            weights = [w1, w2, w3, w4]
            ensemble = np.average(np.stack(prediction_arrays), axis=0, weights=weights)
            return -calculate_rmse(ensemble, reference_array)

        pbounds = {f'w{i+1}': (0, 1) for i in range(num_predictions)}
        print(f'pbounds @{pbounds}')

        optimizer = BayesianOptimization(
            f=bayesian_optimization_function,
            pbounds=pbounds,
            random_state=1,
        )

        
        optimizer.maximize(
            init_points=init_points,
            n_iter=n_iter,
        )

        best_weights = [optimizer.max['params'][f'w{i+1}'] for i in range(num_predictions)]
        print(print(f'best_weights @{best_weights}'))
        optimized_ensemble_array = np.average(np.stack(prediction_arrays), axis=0, weights=best_weights)
        opte_fn = os.path.join(output_dir, f"OPTe_{init_points}_{n_iter}.tif")
        write_raster(optimized_ensemble_array, transform, crs, opte_fn)
        print('==='*40)
        print(f"Optimized ensemble (maximizing RMSE) saved to: {opte_fn}")
        print(f"Optimized weights: {best_weights}")

    return avge_fn, opte_fn

