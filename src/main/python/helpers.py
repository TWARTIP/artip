import numpy
import math
import os

def flatten(elements):
    return list(numpy.array(elements).flatten())

def minus(list1, list2):
    return filter(lambda elm: elm not in list2, list1)


def nCr(n, r):
    f = math.factorial
    return f(n) / f(r) / f(n - r)


def is_last_element(ele, elements):
    return ele == elements[len(elements) - 1]


def delete_indexes(array, indexes):
    result = []
    for index, time_index in enumerate(indexes):
        result = numpy.delete(array, time_index, 0) if index == 0 else numpy.delete(result, time_index - 1, 0)
    return result


def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def calculate_percentage(favourable, total):
    try:
        percentage = (float(favourable) / float(total)) * 100
    except ZeroDivisionError:
        percentage = 0
    return percentage


def format_spw_with_channels(spw_list, channel):
    return ",".join(["{0}:{1}".format(s, channel) for s in spw_list.split(",")])
