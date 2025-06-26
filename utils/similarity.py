import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def calculate_cosine_similarity(vec1, vec2):
    """
    Calculates the cosine similarity between two vectors.
    """
    if vec1 is None or vec2 is None:
        return 0.0

    # Ensure vectors are numpy arrays and reshaped for sklearn
    vec1 = np.array(vec1).reshape(1, -1)
    vec2 = np.array(vec2).reshape(1, -1)

    return cosine_similarity(vec1, vec2)[0][0]
