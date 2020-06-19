import numpy as np


available_sampling_types = ["within_landscape", "change_landscape", "positive", "negative", "centered"]


def get_random_cob(range_cob: int, size: int, sampling_type='within_landscape', center=1) -> np.ndarray:
    """
        Return random change of basis:

        'within_landscape' - in interval [1 - range_cob, 1 + range_cob]
        'change_landscape' - equally in intervals [-1 - range_cob, -1 + range_cob] and [1 - range_cob, 1 + range_cob]
        'positive' - in interval [0, range_cob]
        'negative' - in interval [-range_cob, 0]
        'centered' - in interval [center - range_cob, center + range_cob]

    Args:
        range_cob (int): range_cob for the change of basis. Recommended between 0 and 1, but can take any
        positive range_cob.
        size (int): size of the returned array.
        sampling_type: label for type of sampling for change of basis
        center: The center of the normal distribution with which to sample
    Returns:
        ndarray of size size.
    """
    # Change of basis in interval [1-range_cob, 1+range_cob]
    if sampling_type == 'within_landscape':
        if range_cob > center or center <= 0:
            print('Warning: The current center allows for negative changes of basis.')
        if center != 1:
            print('Warning: The change of basis sampling is not centered at 1')
        return np.random.uniform(low=-range_cob, high=range_cob, size=size).astype(np.float) + 1

    # Change of basis equally in intervals [-1-range_cob, -1+range_cob] and [1-range_cob, 1+range_cob]
    elif sampling_type == 'change_landscape':
        samples = np.random.randint(0, 2, size=size)
        cob = np.zeros_like(samples, dtype=np.float)
        cob[samples == 1] = np.random.uniform(
            low=-1-range_cob, high=-1+range_cob, size=samples.sum())
        cob[samples == 0] = np.random.uniform(
            low=1-range_cob, high=1+range_cob, size=(len(samples) - samples.sum()))
        return cob

    # Change of basis in interval [center- range_cob, center + range_cob]
    elif sampling_type == 'centered':
        if range_cob > center or center <= 0:
            print('Warning: The range for change of basis sampling allows for negative changes of basis.')
        return np.random.uniform(low=center - range_cob, high=center + range_cob, size=size).astype(np.float)

    # Change of basis in interval [0, range_cob]
    elif sampling_type == 'positive':
        return np.random.uniform(low=0, high=range_cob, size=size).astype(np.float)

    # Change of basis in interval [-range_cob, 0]
    elif sampling_type == 'negative':
        return np.random.uniform(low=-range_cob, high=0, size=size).astype(np.float)

    else:
        print('Invalid sampling type: sampling types allowed:')
        print(available_sampling_types)
