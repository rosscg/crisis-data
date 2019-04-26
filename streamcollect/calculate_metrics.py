import networkx as nx

from .models import Event

#TODO: make into async celery task
def calculate_user_graph_metrics(users, relationships):
    #G = nx.read_gexf('gephi_centrality_network_data.gexf')
    G=nx.DiGraph()
    print('adding nodes...')
    for node in users:
        G.add_node(node.screen_name)
    print('adding edges...')
    for relationship in relationships:
        G.add_edge(relationship.source_user.screen_name, relationship.target_user.screen_name)
    print('calculating largest connected_component...')
    # Select largest connected_component:
    G = G.subgraph(max(nx.weakly_connected_components(G), key=len))
    print('calculating degree_centrality...')
    degree_dict = nx.degree_centrality(G)
    print('calculating betweenness_centrality...')
    betweenness_dict = nx.betweenness_centrality(G)
    print('calculating load_centrality...')
    load_dict = nx.load_centrality(G)
    print('calculating eigenvector_centrality...')
    eigenvector_dict = nx.eigenvector_centrality(G)
    #print('calculating katz_centrality...')
    #katz_dict = nx.katz_centrality(G)  # Currently throwing PowerIterationFailedConvergence
    print('calculating closeness_centrality...')
    closeness_dict = nx.closeness_centrality(G)
    #maximum = max(eigenvector_dict, key=eigenvector_dict.get)
    #print('max eigenvector node: {}: {}'.format(maximum, eigenvector_dict[maximum]))
    # Create undirected graph to calculate undirected centralities:
    print('calculating undirected eigenvector_centrality...')
    undirected_G = G.to_undirected()
    undirected_eigenvector_dict = nx.eigenvector_centrality(undirected_G)
    print('saving metrics to user objects...')
    for user in users:
        try:
            user.degree_centrality = degree_dict[user.screen_name]
            user.betweenness_centrality = betweenness_dict[user.screen_name]
            user.load_centrality = load_dict[user.screen_name]
            user.eigenvector_centrality = eigenvector_dict[user.screen_name]
            #user.katz_centrality = katz_dict[user.screen_name]
            user.closeness_centrality = closeness_dict[user.screen_name]
            user.undirected_eigenvector_centrality = undirected_eigenvector_dict[user.screen_name]
            user.save()
        except:
            # User not part of largest connected component.
            pass
    # Write to file for testing in Gephi:
    nx.write_gexf(G, 'gephi_centrality_network_data.gexf', prettyprint=True)


def calculate_user_stream_metrics(users):
    e = Event.objects.all()[0]
    time_delta = max(e.kw_stream_end, e.gps_stream_end) - min(e.kw_stream_start, e.gps_stream_start)
    stream_length = (time_delta.days * 24) + (time_delta.seconds / 60 / 60)
    for user in users:
        total = user.tweet.all().count()
        detected = user.tweet.filter(data_source__gt=0).count()
        added = user.tweet.filter(data_source=0).count()
        media_count = user.tweet.filter(media_files__isnull=False).count()
        user.ratio_original = user.tweet.filter(in_reply_to_status_id__isnull=True, in_reply_to_user_id__isnull=True, quoted_status_id_int__isnull=True).count() / total
        user.ratio_detected = detected / total
        user.ratio_media = media_count / total
        user.tweets_per_hour = user.tweet.all().count() / stream_length
        user.save()
