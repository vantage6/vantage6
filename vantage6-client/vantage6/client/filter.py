import functools
from typing import Any


#
# Decorators
#
def filter_dicts_from_results(func: callable) -> callable:
    """Filter a list of dicts.

    Based on a key-value pair within the dict. A single key-value pair can be
    given through the argument `filter_` OR a list of key-value pairs can be
    given through the argument `filters`. Note that if the key is not present
    the key is ignored completely.

    Parameters
    ----------
    func : callable
        The function that returns a list of dicts.

    Returns
    -------
    callable
        The function that returns a list of dicts, filtered by the specified
        filters.
    """

    @functools.wraps(func)
    def wrapper_filter(
        *args,
        filter_: tuple[Any, Any] = None,
        filters: list[tuple[Any, Any]] = None,
        **kwargs
    ) -> list[dict]:
        """
        Apply filters to the results of the function.

        Parameters
        ----------
        *args
            Positional arguments for the function.
        filter_ : tuple[Any, Any], optional
            A single key-value pair to filter on, by default None
        filters : list[tuple[Any, Any]], optional
            A list of key-value pairs to filter on, by default None

        Returns
        -------
        list[dict]
            The filtered list of dicts.
        """
        dicts = func(*args, **kwargs)
        if filter_:
            return filter_dicts_by_values(dicts, [filter_])
        return filter_dicts_by_values(dicts, filters)

    return wrapper_filter


def filter_keys_from_result(func: callable) -> callable:
    """Wrapper to filter key-value pairs from a dict.

    Removes key-value pair based on the key from a dict. If the key is not
    present in the dict it is ignored.

    Parameters
    ----------
    func : callable
        The function that returns a dict.

    Returns
    -------
    callable
        The function that returns a dict, with only the specified keys kept.
    """

    @functools.wraps(func)
    def wrapper_filter(
        *args, field: Any = None, fields: list[Any] = None, **kwargs
    ) -> dict:
        """
        Apply filters to the results of the function. If no filters are given,
        the function returns the original dict.

        Parameters
        ----------
        *args
            Positional arguments for the function.
        field : Any, optional
            A single key to filter the dictionary on, by default None
        fields : list[Any], optional
            A list of keys to filter the dictionary on, by default None

        Returns
        -------
        dict
            The filtered dictionary.
        """
        dict_ = func(*args, **kwargs)
        if field:
            return filter_dict_keys(dict_, [field])
        return filter_dict_keys(dict_, fields)

    return wrapper_filter


def filter_keys_from_results(func: callable) -> callable:
    """Remove key-value pairs from a list of dicts.

    Removes key-value pair of all dictornairies in the list. If the key is not
    present in the dicts it is ignored.

    Parameters
    ----------
    func : callable
        The function that returns a list of dicts.

    Returns
    -------
    callable
        The function that returns a list of dicts, with only the specified keys
    """

    @functools.wraps(func)
    def wrapper_filter(
        *args, field: Any = None, fields: list[Any] = None, **kwargs
    ) -> list[dict]:
        """
        Apply filters to the results of the function. If no filters are given,
        the function returns the list of dicts.

        Parameters
        ----------
        *args
            Positional arguments for the function.
        field : Any, optional
            A single key to filter the dictionaries on, by default None
        fields : list[Any], optional
            A list of keys to filter the dictionary on, by default None

        Returns
        -------
        list[dict]
            The filtered list of dicts.
        """
        dict_ = func(*args, **kwargs)
        if field:
            return filter_dicts_keys(dict_, [field])
        return filter_dicts_keys(dict_, fields)

    return wrapper_filter


def post_filtering(iterable: bool = True) -> callable:
    """Decorator to add filtering of dictornaries from the result.

    Depending on whether this is a list of or a single dictionairy, the
    decorator adds the arguments field, fields, filter, filters.

    This is a wrapper for the other decorators. Note that the order of
    `filter_keys_from_results` and `filter_dicts_from_results` is important as
    you do want to first select the dicts that you need and then filter their
    keys. This way you can filter on key-value pairs that you do not want in
    your output.

    Parameters
    ----------
    iterable : bool, optional
        Whether the result is a list of dicts or a single dict, by default True

    Returns
    -------
    callable
        The original function with the added decorators that filter the output
        of the function by specified fields and keys.
    """

    def decorator(func):
        if iterable:

            @functools.wraps(func)
            @filter_keys_from_results
            @filter_dicts_from_results
            def wrapper_filter(*args, **kwargs):
                return func(*args, **kwargs)

        else:

            @functools.wraps(func)
            @filter_keys_from_result
            def wrapper_filter(*args, **kwargs):
                return func(*args, **kwargs)

        return wrapper_filter

    return decorator


#
# Helper functions
#
def filter_dicts_on_values(
    dicts: list[dict], filters: list[tuple[Any, Any]]
) -> list[dict]:
    """
    Filter a list of dicts on the specified key-value pairs.

    Parameters
    ----------
    dicts : list[dict]
        The list of dicts to filter.
    filters : list[tuple[Any, Any]]
        A list of key-value pairs to filter on.

    Returns
    -------
    list[dict]
        The filtered list of dicts.
    """
    filtered_dicts = []
    resource_list = dicts["data"] if "data" in dicts else dicts
    for dict_ in resource_list:
        if all([dict_[filter_[0]] == filter_[1] for filter_ in filters]):
            filtered_dicts.append(dict_)
    return filtered_dicts


def filter_dicts_by_values(
    dicts: list[dict], filters: list[tuple[Any, Any]]
) -> list[dict]:
    """
    Filter a list of dicts on the specified key-value pairs.

    Parameters
    ----------
    dicts : list[dict]
        The list of dicts to filter.
    filters : list[tuple[Any, Any]]
        A list of key-value pairs to filter on.

    Returns
    -------
    list[dict]
        The filtered list of dicts.
    """
    if filters:
        return filter_dicts_on_values(dicts, filters)
    return dicts


def filter_dicts_keys(dict_: dict, keys: list[str]) -> list[dict]:
    """
    Filter a list of dicts on the specified keys. If no keys are given, the
    original list of dicts is returned.

    Parameters
    ----------
    dicts : list[dict]
        The dict to filter. This is a dict with a 'data' key that contains the
        list of data dictionaries that will be filtered.
    keys : list[str]
        A list of keys to keep in the dictionaries

    Returns
    -------
    list[dict]
        The filtered list of dicts.
    """
    # note: we look only in the 'data' key of the dict, which contains the list
    # of data. The only other key is 'links' which contains pagination links
    if keys:
        return [filter_dict_keys(adict, keys) for adict in dict_["data"]]
    return dict_


def filter_dict_keys(dict_: dict, keys: list[str]) -> dict:
    """
    Filter a dict on the specified keys. If no keys are given, the original
    dict is returned.

    Parameters
    ----------
    dict_ : dict
        The dict to filter.
    keys : list[str]
        A list of keys to keep in the dictionary

    Returns
    -------
    dict
        The filtered dict.
    """
    return {k: dict_[k] for k in keys if k in dict_} if keys else dict_
