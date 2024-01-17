import math
import threading

from .BreadthFirstSearch import BreadthFirstSearch
from .model.Node import Node
from .model.Path import Path
from .model.PathContainer import PathContainer


class BidirectionalPathFinder:

    def __init__(self, repository):
        self.repo = repository

    def find_all_paths(self, node_id_1, node_id_2, hops_numbers=1):
        result = set()
        if hops_numbers == 0:
            return result
        if node_id_1 == node_id_2:
            return result

        hops_numbers_1 = math.floor((hops_numbers + 1) / 2)
        hops_numbers_2 = math.floor(hops_numbers / 2)

        path_container_1 = PathContainer()
        bfs_1 = BreadthFirstSearch(self.repo, path_container_1)

        path_container_2 = PathContainer()
        bfs_2 = BreadthFirstSearch(self.repo, path_container_2)

        thread_1 = threading.Thread(target=lambda: bfs_1.traverse(node_id_1, hops_numbers_1))
        thread_2 = threading.Thread(target=lambda: bfs_2.traverse(node_id_2, hops_numbers_2))
        thread_1.start()
        thread_2.start()
        thread_1.join()
        thread_2.join()

        intersection_list = path_container_1.path_dict.keys() & path_container_2.path_dict.keys()

        for node in intersection_list:
            for path_1 in path_container_1.path_dict[node]:
                for path_2 in path_container_2.path_dict[node]:
                    temp_path_1 = [Node(link.id, link.weight) for link in path_1.links]
                    temp_path_2 = [Node(link.id, link.weight) for link in path_2.links]
                    temp_path_2.pop()
                    if len(temp_path_2) != 0:
                        temp_path_2.reverse()
                        temp_path_1.extend(temp_path_2)
                    if len(temp_path_1) == len(set(temp_path_1)):
                        result.add(Path(0, temp_path_1))

        result = sorted(list(result), key=lambda path: path.compute_weight())

        return result
