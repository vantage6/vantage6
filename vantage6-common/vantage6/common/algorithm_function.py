def is_vantage6_algorithm_func(func: callable) -> bool:
    """
    Check if the function is decorated with a vantage6 decorator, which all
    functions being called in vantage6 algorithm should be

    Parameters
    ----------
    func : callable
        The function to check

    Returns
    -------
    bool
        True if the function is decorated with a vantage6 decorator, False otherwise
    """
    return get_vantage6_decorator_type(func) is not None


def get_vantage6_decorator_type(func: callable) -> str | None:
    """
    Get the vantage6 decorator type of the function

    Parameters
    ----------
    func : callable
        The function to get the vantage6 decorator type of

    Returns
    -------
    str | None
        The vantage6 decorator type of the function, or None if the function is not
        decorated with a vantage6 decorator
    """
    return getattr(func, "vantage6_decorator_step_type", None)
