import networkx as nx


def create_gephi_file(relevant_users, relevant_relos):
    G=nx.DiGraph()
    for node in relevant_users:
        G.add_node(node.screen_name, user_class=node.user_class)
    for relo in relevant_relos:
        G.add_edge(relo.source_user.screen_name, relo.target_user.screen_name)

    nx.write_gexf(G, 'gephi_network_data.gexf', prettyprint=True)
    return


def create_csv_file(relevant_relos):
    csv = open('data_csv.csv','w')
    for relo in relevant_relos:
        csv.write(relo.as_csv()+'\n')
    csv.close()
    return
