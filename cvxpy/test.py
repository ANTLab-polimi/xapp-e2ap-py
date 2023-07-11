import cvxpy as cp
import numpy as np
from time import time

NODE_CAPACITY = 106
PRINT_VARS = False

def main():

    tic_tree = time()
    nodes, ues = get_topology_flexible()
    constraints = []

    print("{} IAB nodes, {} UEs".format(len(nodes), len(ues)))
    print("Tree generation time: {} ms".format((time()-tic_tree)*1000))
    print(" \n_____________________")


    tic_gen = time()
    # capacity constraints
    for node in nodes.values():
        constraints += node.constraint(ues)

    # variable domain
    for ue in ues.values():
        constraints += [ue.rate >= 0]

    objective_maxlog = cp.Maximize(sum(cp.log(ue.rate) for ue in ues.values()))
    objective_maxsum = cp.Maximize(sum(ue.rate for ue in ues.values()))
    prob_maxlog = cp.Problem(objective_maxlog, constraints)
    prob_maxsum = cp.Problem(objective_maxsum, constraints)

    print("Problem generation time: {} ms".format((time()-tic_gen)*1000))
    print(" \n_____________________")

    tic_maxlog = time()
    prob_maxlog.solve()
    tic_maxlog = time() - tic_maxlog

    print("Maxlog solved in {} ms".format(tic_maxlog*1000))
    print("Objective: {}".format(prob_maxlog.value))
    if PRINT_VARS:
        print("Variables:")
        for ue in ues.values():
            print("{} = {}".format(ue.rate, ue.rate.value))
    print("Sum rates: {}".format(sum(ue.rate.value for ue in ues.values())))

    tic_maxsum = time()
    prob_maxsum.solve()
    tic_maxsum = time() - tic_maxsum

    print(" \n_____________________")
    print("Maxsum solved in {} ms".format(tic_maxsum*1000))
    print("Objective: {}".format(prob_maxsum.value))
    if PRINT_VARS:
        print("Variables:")
        for ue in ues.values():
            print("{} = {}".format(ue.rate, ue.rate.value))
    print("Sum rates: {}".format(sum(ue.rate.value for ue in ues.values())))

class Node(object):
    def __init__(self,capacity,id) -> None:
        self.capacity = capacity
        self.id = id
        self.costs = {}
        self.children = []
        self.parent = None
    def __str__(self):
        return "node id: {}, costs: {}".format(self.id, self.costs)
    
    def constraint(self, ues):
        uei = ues.values()
        return [sum(ue.rate * self.costs[ue.id] for ue in uei) <= self.capacity]

class Ue(object): 
    def __init__(self,id) -> None:
        self.rate=cp.Variable(name="{}.rate".format(id))
        self.id = id
        self.parent = None

def random_cost():
    return 1 + np.random.rand()*9

def get_topology():
    nodes = {}
    ues = {}
    standard_capacity = 106

    # add donor and nodes
    nodes['donor'] = Node(capacity=standard_capacity, id='donor')
    nodes['iab_1'] = Node(capacity=standard_capacity, id='iab_1')
    nodes['iab_2'] = Node(capacity=standard_capacity, id='iab_2')

    # add costs of children, iab_1 cost is taken from the e2 message, iab_2 cost is same as iab_1 since it is a child of it
    nodes['donor'].costs['iab_1'] = random_cost()
    nodes['donor'].costs['iab_2'] = nodes['donor'].costs['iab_1']
    nodes['iab_1'].costs['iab_2'] = random_cost()
    
    # add this ue to the donor with cost taken from e2 and to all the others nodes with cost 0
    ues['donor_ue_1'] = Ue(id='donor_ue_1')
    nodes['donor'].costs['donor_ue_1'] = random_cost()
    nodes['iab_1'].costs['donor_ue_1'] = 0
    nodes['iab_2'].costs['donor_ue_1'] = 0

    # add this ue to the donor with cost taken from e2 and to all the others nodes with cost 0
    ues['donor_ue_2'] = Ue(id='donor_ue_2')
    nodes['donor'].costs['donor_ue_2'] = random_cost()
    nodes['iab_1'].costs['donor_ue_2'] = 0
    nodes['iab_2'].costs['donor_ue_2'] = 0


    # same as before, add here and with cost given by topology elsewhere
    ues['iab_1_ue_1'] = Ue(id='iab_1_ue_1')
    nodes['iab_1'].costs['iab_1_ue_1'] = random_cost()
    nodes['donor'].costs['iab_1_ue_1'] = nodes['donor'].costs['iab_1']
    nodes['iab_2'].costs['iab_1_ue_1'] = 0

    ues['iab_1_ue_2'] = Ue(id='iab_1_ue_2')
    nodes['iab_1'].costs['iab_1_ue_2'] = random_cost()
    nodes['donor'].costs['iab_1_ue_2'] = nodes['donor'].costs['iab_1']
    nodes['iab_2'].costs['iab_1_ue_2'] = 0

    # iab depth 2
    ues['iab_2_ue_1'] = Ue(id='iab_2_ue_1')
    nodes['iab_2'].costs['iab_2_ue_1'] = random_cost()
    nodes['iab_1'].costs['iab_2_ue_1'] = nodes['iab_1'].costs['iab_2']
    nodes['donor'].costs['iab_2_ue_1'] = nodes['donor'].costs['iab_1']

    ues['iab_2_ue_2'] = Ue(id='iab_2_ue_2')
    nodes['iab_2'].costs['iab_2_ue_2'] = random_cost()
    nodes['iab_1'].costs['iab_2_ue_2'] = nodes['iab_1'].costs['iab_2']
    nodes['donor'].costs['iab_2_ue_2'] = nodes['donor'].costs['iab_1']

    return nodes, ues

def get_topology_flexible():
    max_depth = 3
    max_children = 2
    n_ues_per_node = 8
    tree = build_tree(max_depth,max_children)
    nodes = {}
    ues = {}
    save_tree(tree, nodes)
    add_ues(n_ues_per_node,nodes,ues)
    return nodes, ues


def build_tree(max_depth, max_children, current_depth=0, node_id=0):
    if current_depth >= max_depth:
        return None

    node = Node(NODE_CAPACITY,str(node_id))
    for i in range(max_children):
        child_id = node_id * max_children + (i + 1)
        child = build_tree(max_depth, max_children, current_depth + 1, child_id)
        if child:
            node.children.append(child)
            child.parent = node
            node.costs[child.id] = random_cost()
    return node

def save_tree(node, node_dict):
    if node is None:
        return

    node_dict[node.id] = node

    for child in node.children:
        save_tree(child, node_dict)

def add_ues(n_ues,nodes,ues):
    for node in nodes.values():
        for u in range(0,n_ues):
            ueid = node.id + '_ue' + str(u)
            ue = Ue(ueid)
            ues[ueid] = ue
            update_ue_costs(node, ueid, nodes)

def update_ue_costs(parent_node,ueid, all_nodes):
    parent_node.costs[ueid] = random_cost()
    unvisited_nodes = all_nodes.copy()
    del unvisited_nodes[parent_node.id]
    while parent_node.parent:
        parent_node.parent.costs[ueid] = parent_node.parent.costs[parent_node.id]
        parent_node = parent_node.parent
        del unvisited_nodes[parent_node.id]
    for unvisited_node in unvisited_nodes.values():
        unvisited_node.costs[ueid] = 0



if __name__ == "__main__":
    main()