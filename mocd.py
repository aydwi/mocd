#!/usr/bin/env python3

import pprint

from collections import defaultdict


"""
:TEST DATA:
{
    "cpu_0": [
        "cpu_0.0 STORE 0x2",
        "cpu_0.1 LOAD  0x1",
        "cpu_0.2 LOAD  0x1",
        "cpu_0.3 LOAD  0x4",
        "cpu_0.4 LOAD  0x3",
    ],
    "cpu_1": [
        "cpu_1.0 STORE 0x1",
        "cpu_1.1 LOAD  0x2",
        "cpu_1.2 STORE 0x3",
        "cpu_1.3 STORE 0x4",
        "cpu_1.4 LOAD  0x4",
    ],
}
"""

def _merge_graphs(self, graph_one: dict, graph_two: dict) -> dict:
    merged_graph = defaultdict(list)

    for key in set().union(graph_one, graph_two):
        for dic in [graph_one, graph_two]:
            if key in dic:
                merged_graph[key] += dic[key]

    merged_graph = dict(merged_graph)

    for k, v in merged_graph.items():
        merged_graph[k] = list(set(v))

    return merged_graph


class MemoryCycle:
    def __init__(self, cpus: list) -> None:

        self.cpus = cpus
        self.stream = []
        self.dgraph = {}
        self.ograph = {}
        self.igraph = {}


    def read_stream(self) -> None:
        for cpu in self.cpus:
            cpu_name = cpu.split(".")[0]
            with open(cpu, "r") as f:
                self.stream.append([cpu_name + "." + line.rstrip() for line in f])

    def is_cyclic(self, graph: dict) -> bool:
        path = set()
        visited = set()

        def visit(vertex):
            if vertex in visited:
                return False
            visited.add(vertex)
            path.add(vertex)
            for neighbour in graph.get(vertex, ()):
                if neighbour in path or visit(neighbour):
                    return True
            path.remove(vertex)
            return False

        return any(visit(v) for v in graph)

    def build_direct_graph(self) -> None:
        for cpu in self.stream:
            for index, instruction in enumerate(cpu):
                instruction = instruction.split(" ")[0]
                try:
                    self.dgraph[instruction] = [cpu[index + 1].split(" ")[0]]
                except IndexError:
                    pass

    def build_observability_graph(self) -> None:
        load = []

        for cpu in self.stream:
            for ins in cpu:
                index, _, rest = ins.partition(" ")
                op, _, add = rest.partition(" ")
                op, add = op.strip(), add.strip()
                if op == "LOAD":
                    load.append([index, add])

        for cpu in self.stream:
            for ins in cpu:
                index, _, rest = ins.partition(" ")
                op, _, add = rest.partition(" ")
                op, add = op.strip(), add.strip()
                if op == "STORE":
                    for load_op in load:
                        if load_op[-1] == add:
                            try:
                                self.ograph[index].append(load_op[0])
                            except KeyError:
                                self.ograph[index] = [load_op[0]]

    # One of the inference type discussed during the iterview,
    # where edges are made from every instruction above a STORE
    # to it's LOAD. No longer used.
    """
    def build_inferred_above_store(self) -> None:
        for key, value in self.ograph.items():
            for i, list_val in enumerate(self.stream):
                for j, internal_val in enumerate(list_val):
                    if key == internal_val.split(" ")[0]:
                        cnt = j
                        for x in self.stream[i]:
                            if cnt > 0:
                                x_trim = x.split(" ")[0]
                                try:
                                    self.igraph[x_trim].append(self.ograph[key])
                                except KeyError:
                                    self.igraph[x_trim] = [self.ograph[key]]
                                cnt -= 1

        # Flatten every value from list of lists to list
        for key, val in self.igraph.items():
            self.igraph[key] = [x for sublist in val for x in sublist]
    """

    def build_inferred_graph(self) -> None:

        lean_ograph = {}
        temp_stream = []

        # Used for comparison later instead of vanilla stream
        for i in self.stream:
            temp_stream.append([x.split(" ")[0] for x in i])

        # PART 1 of inferred graph

        # Optimization to avoid generating redundant edges
        # Generates an optimized ograph by removing second
        # till last value for every cpu against a key, and
        # also removing self edges. The former works because
        # every CPU executes it's instructions in order, and
        # the latter works because dgraph already covers the
        # situation
        for key, val in self.ograph.items():
            new_val = []
            category_store = []
            for i in val:
                category = i.split(".")[0]
                if category not in category_store and category != key.split(".")[0]:
                    category_store.append(category)
                    new_val.append(i)
            lean_ograph[key] = new_val

        for key, val in lean_ograph.items():
            for num, cpu in enumerate(temp_stream):
                for i, unit in enumerate(cpu):
                    for v in val:
                        if v == unit:
                            # Uncomment the print statement below to see the
                            # inferred edges being drawn. Also, replace lean_ograph
                            # with self.ograph to see the un-optimized calculation
                            """
                            print(
                                "Create edges, starting at index "
                                + str(i)
                                + " in CPU "
                                + str(num)
                                + ", against the key "
                                + key
                            )
                            """
                            for node_index in range(i, len(temp_stream[num])):
                                try:
                                    self.igraph[key].append(
                                        temp_stream[num][node_index]
                                    )
                                except KeyError:
                                    self.igraph[key] = [temp_stream[num][node_index]]

        # PART 2 of inferred graph

        igraph2 = {}

        for key, val in self.ograph.items():
            for v in val:
                # Look up v's key's identity in temp_stream
                for cpu in temp_stream:
                    try:
                        index = cpu.index(key)
                    except ValueError:
                        pass
                    else:
                        # Form additional edges here
                        for i, op in enumerate(cpu):
                            if i > index:
                                try:
                                    igraph2[v].append(op)
                                except KeyError:
                                    igraph2[v] = [op]
        
        # Remove STORE mappings from every LOAD after forming the inital edges
        for key, val in igraph2.items():
            for v in val:
                for cpu in self.stream:
                    for ins in cpu:
                        index, _, rest = ins.partition(" ")
                        op, _, add = rest.partition(" ")
                        op, add = op.strip(), add.strip()
                        if index == v and op == "STORE":
                            igraph2[key].remove(v)
        pp.pprint(igraph2)


if __name__ == "__main__":
    pp = pprint.PrettyPrinter()
    o = MemoryCycle(["cpu_0.txt", "cpu_1.txt"])

    o.read_stream()
    o.build_direct_graph()
    o.build_observability_graph()
    o.build_inferred_graph()
