def check_cuts(cuts):
    """transform tuple into a merged dict"""
    if isinstance(cuts, tuple):
        merged_dict = {k: v for d in cuts for k, v in d.items()}
        return merged_dict.copy()
    return cuts.copy()