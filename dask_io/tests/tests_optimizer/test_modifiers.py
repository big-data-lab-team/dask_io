import os

from dask_io.utils.utils import CHUNK_SHAPES_EXP1
from dask_io.utils.array_utils import get_arr_shapes
from dask_io.utils.get_arrays import get_dask_array_from_hdf5

from dask_io.cases.case_config import CaseConfig

from dask_io.optimizer.modifiers import *


# TODO: make tests with different chunk shapes
data_dirpath = 'data'
array_filepath = os.path.join(data_dirpath, 'sample_array_nochunk.hdf5')
log_dir = "dask_io/logs"


def test_add_to_dict_of_lists():
    d = {'a': [1], 'c': [5, 6]}
    d = add_to_dict_of_lists(d, 'b', 2)
    d = add_to_dict_of_lists(d, 'b', 3)
    d = add_to_dict_of_lists(d, 'c', 4)
    expected = {'a': [1], 'b': [2, 3], 'c': [5, 6, 4]}
    assert expected == d


def test_get_array_block_dims():
    shape = (500, 1200, 300)
    chunks = (100, 300, 20)
    block_dims = get_array_block_dims(shape, chunks)
    expected = (5, 4, 15)
    assert block_dims == expected


def test_flatten_iterable():
    l = [0, [1, 2, 3], 4, [5], [[6, 7]]]
    assert flatten_iterable(l, list()) == list(range(8))


def test_get_graph_from_dask():
    # create config for the test
    case = CaseConfig(array_filepath, "auto")
    case.sum(nb_chunks=2)
    dask_array = case.get()

    # test function
    dask_graph = dask_array.dask.dicts 
    graph = get_graph_from_dask(dask_graph, undirected=False)
    with open(os.path.join(log_dir, 'get_graph_from_dask.txt'), "w+") as f:
        for k, v in graph.items():
            f.write("\n\n" + str(k))
            f.write("\n" + str(v))


def test_get_used_proxies():
    for chunk_shape_key in list(CHUNK_SHAPES_EXP1.keys()):
        cs = CHUNK_SHAPES_EXP1[chunk_shape_key]

        case = CaseConfig(array_filepath, cs)
        case.sum(nb_chunks=2)
        
        for use_BFS in [True]: #, False]:
            dask_array = get_dask_array_from_hdf5(case.array_filepath, '/data', to_da=True, logic_cs=cs)
            
            """dask.config.set({
                'io-optimizer': {
                    'chunk_shape': cs
                }
            })"""

            # test function
            dask_graph = dask_array.dask.dicts 
            _, dicts = get_used_proxies(dask_graph, use_BFS=True)
            
            # test slices values
            slices = list(dicts['proxy_to_slices'].values())
            if "blocks" in chunk_shape_key:
                s1 = (slice(0, cs[0], None), slice(0, cs[1], None), slice(0, cs[2], None))
                s2 = (slice(0, cs[0], None), slice(0, cs[1], None), slice(cs[2], 2 * cs[2], None))
            else:
                s1 = (slice(0, cs[0], None), slice(0, cs[1], None), slice(0, cs[2], None))
                s2 = (slice(cs[0], 2 * cs[0], None), slice(0, cs[1], None), slice(0, cs[2], None))

            print("\nExpecting:")
            print(s1)
            print(s2)

            print("\nGot:")
            print(slices[0])
            print(slices[1])

            assert slices == [s1, s2]


def test_BFS():
    graph = {
        'a': ['b', 'c'],
        'b': [],
        'c': ['d', 'e'],
        'd': [],
        'e': [],
        'f': ['e']
    }
    values, depth = standard_BFS('a', graph)
    assert values == ['a', 'b', 'c', 'd', 'e']
    assert depth == 2

    values, depth = standard_BFS('f', graph)
    assert values == ['f', 'e']
    assert depth == 1


def test_get_unused_keys():
    graph = {
        'a': ['b', 'c'],
        'b': [],
        'c': ['d', 'e'],
        'd': [],
        'e': [],
        'f': ['e']
    }
    root_nodes = get_unused_keys(graph)
    assert root_nodes == ['a', 'f']


def test_BFS_2():
    """ test to include bfs in the program
    """
    graph = {
        'a': ['b', 'c'],
        'b': [],
        'c': ['d', 'e'],
        'd': [],
        'e': [],
        'f': ['e']
    }
    root_nodes = get_unused_keys(graph)

    max_components = list()
    max_depth = 0
    for root in root_nodes:
        node_list, depth = standard_BFS(root, graph)
        if len(max_components) == 0 or depth > max_depth:
            max_components = [node_list]
            max_depth = depth
        elif depth == max_depth:
            max_components.append(node_list)

    assert max_depth == 2
    assert len(max_components) == 1
    assert max_components[0] == ['a', 'b', 'c', 'd', 'e']


def test_BFS_3():
    """ test to include bfs in the program and test with rechunk case
    """

    # get test array with logical rechunking
    chunks_shape = (770, 605, 700)

    case = CaseConfig(array_filepath, chunks_shape)
    case.sum(nb_chunks=2)
    dask_array = case.get()
    # dask_array.visualize(filename='tests/outputs/img.png', optimize_graph=False)

    # get formatted graph for processing
    graph = get_graph_from_dask(dask_array.dask.dicts, undirected=False)  # we want a directed graph

    with open(os.path.join(log_dir, 'test_BFS_3.txt'), "w+") as f:
        for k, v in graph.items():
            f.write("\n\n" + str(k))
            f.write("\n" + str(v))

    # test the actual program
    root_nodes = get_unused_keys(graph)
    print('\nRoot nodes:')
    for root in root_nodes:
        print(root)

    max_components = list()
    max_depth = 0
    for root in root_nodes:
        node_list, depth = standard_BFS(root, graph)
        if len(max_components) == 0 or depth > max_depth:
            max_components = [node_list]
            max_depth = depth
        elif depth == max_depth:
            max_components.append(node_list)


    print("nb components found:", str(len(max_components)))
    #TODO: assertions