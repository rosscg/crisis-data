import networkx as nx


def create_gephi_file(relevant_users, relevant_relos):
    G=nx.DiGraph()
    for node in relevant_users:

        best_code = ''
        for t in node.tweet.all():
            for c in t.coder.all():
                if (best_code == '' or c.data_code.data_code_id < best_code) and c.data_code.data_code_id > 0:
                    best_code = c.data_code.data_code_id

        G.add_node(node.screen_name, user_class=node.user_class, best_code=best_code)

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
