import functools


#
# Decorators
#
def filter_dicts_from_results(func):
    """ Filter a list of dicts.

    Based on a key-value pair within the dict. A single key-value pair can be
    given through the argument `filter_` OR a list of key-value pairs can be
    given through the argument `filters`. Note that if the key is not present
    the key is ignored completely.
    """
    @functools.wraps(func)
    def wrapper_filter(*args, filter_=None, filters=None, **kwargs):
        dicts = func(*args, **kwargs)
        if filter_:
            return filter_dicts_by_values(dicts, [filter_])
        return filter_dicts_by_values(dicts, filters)
    return wrapper_filter


def filter_keys_from_result(func):
    """ Removes key-value pairs from a dict.

    Removes key-value pair based on the key from a dict. If the key is not
    present in the dict it is ignored.
    """
    @functools.wraps(func)
    def wrapper_filter(*args, field=None, fields=None, **kwargs):
        dict_ = func(*args, **kwargs)
        if field:
            return filter_dict_keys(dict_, [field])
        return filter_dict_keys(dict_, fields)
    return wrapper_filter


def filter_keys_from_results(func):
    """ Remove key-value pairs from a list of dicts.

    Removes key-value pair of all dictornairies in the list. If the key is not
    present in the dicts it is ignored.
    """

    @functools.wraps(func)
    def wrapper_filter(*args, field=None, fields=None, **kwargs):
        dicts = func(*args, **kwargs)
        if field:
            return filter_dicts_keys(dicts, [field])
        return filter_dicts_keys(dicts, fields)
    return wrapper_filter


def post_filtering(iterable=True):
    """Add filtering of dictornaries from the result.

    Depening on wenever this is a list of- or a single dictonairy the decorator
    adds the arguments field, fields, filter, filters.

    This is a wrapper for the other decorators. Note that the order of
    `filter_keys_from_results` and `filter_dicts_from_results` is important as
    you do want to first select the dicts that you need and then filter their
    keys. This way you can filter on key-value pairs that you do not want in
    your output.
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
def filter_dicts_on_values(dicts: list, filters: list) -> list:
    filtered_dicts = []
    for dict_ in dicts:
        if all([dict_[filter_[0]] == filter_[1] for filter_ in filters]):
            filtered_dicts.append(dict_)
    return filtered_dicts


def filter_dicts_by_values(dicts: list, filters: list) -> list:
    if filters:
        return filter_dicts_on_values(dicts, filters)
    return dicts


def filter_dicts_keys(dicts: list, keys: list) -> list:
    if keys:
        return [filter_dict_keys(adict, keys) for adict in dicts]
    return dicts


def filter_dict_keys(dict_, keys):
        return {k: dict_[k] for k in keys if k in dict_} if keys else dict_
