import requests
import pandas as pd


def get_summoner_info(summoner_name, apikey):
    # This function takes the summoner name and the API Key
    # and retrieves its account id
    url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}'
    html = requests.get(url,
                        params={'api_key': apikey})
    json = html.json()
    df = pd.DataFrame(json, index=[0])

    return df


def get_matchlist(accountid, api):
    url = f'https://euw1.api.riotgames.com/lol/match/v4/matchlists/by-account/{accountid}'
    html = requests.get(url,
                        params={'api_key': api})
    json = html.json()
    df = pd.DataFrame(json['matches'])

    return df


def get_match_info(matchid, api):
    url = f'https://euw1.api.riotgames.com/lol/match/v4/matches/{matchid}'
    html = requests.get(url,
                        params={'api_key': api})
    json = html.json()

    return json


def get_players_info(json):
    players = pd.DataFrame()

    for participant in range(10):
        df = pd.DataFrame.from_dict(json['participants'][participant]['stats'], orient='index').T
        df.insert(loc=0, column='championId', value=json['participants'][participant]['championId'])
        df.insert(loc=1, column='teamId', value=json['participants'][participant]['teamId'])

        dff = pd.DataFrame.from_dict(json['participantIdentities'][participant]['player'], orient='index').T
        dff.insert(loc=0, column='participantId', value=json['participantIdentities'][participant]['participantId'])
        df_final = pd.merge(df, dff, on='participantId')

        players = players.append(df_final)

    players.insert(loc=0, column='gameid', value=[json['gameId'] for value in range(len(players))])

    return players


def get_match_timeline(matchid, api):
    url = f'https://euw1.api.riotgames.com/lol/match/v4/timelines/by-match/{matchid}'
    html = requests.get(url,
                        params={'api_key': api})
    json = html.json()

    return json


def participant_frames(json, playersinfo):
    ## Extracting frames from json

    all_frames = pd.DataFrame()

    for frame in list(range(len(json['frames']))):
        iterable = json['frames'][frame]['participantFrames']
        for elem in iterable:
            dic = {}
            for sub_elem in iterable[elem]:
                if type(iterable[elem][sub_elem]) == dict:
                    dic.update(iterable[elem][sub_elem])
                else:
                    dic[sub_elem] = iterable[elem][sub_elem]
            df = pd.DataFrame(dic, index=[0])
            df.insert(loc=0, column='timestamp', value=json['frames'][frame]['timestamp'])
            all_frames = all_frames.append(df, ignore_index=True)

    cols = ['timestamp', 'participantId', 'x', 'y', 'currentGold', 'totalGold', 'level',
            'xp', 'minionsKilled', 'jungleMinionsKilled',
            # 'dominionScore','teamScore',
            ]
    all_frames = all_frames[cols]

    teams = playersinfo[['participantId', 'teamId']]
    frames = pd.merge(all_frames, teams, on='participantId')
    frames['timestamp'] = (frames['timestamp'] / 60000).astype('int')

    return frames


def get_events(json):
    events = pd.DataFrame()

    frames = json['frames']
    for elem in range(len(frames)):
        events = events.append(pd.DataFrame(frames[elem]['events']))

    events['position_x'] = [elem.get('x') if type(elem) == dict else 'none' for elem in events['position']]
    events['position_y'] = [elem.get('y') if type(elem) == dict else 'none' for elem in events['position']]
    events.drop(columns='position', inplace=True)

    return events


def gold_diff(frames):
    data = frames.groupby(['timestamp', 'teamId']).sum().reset_index()[['timestamp', 'teamId', 'totalGold']]

    team100gold = data[data['teamId'] == 100]
    team100gold.rename(columns={"totalGold": "team100gold"}, inplace=True)
    team200gold = data[data['teamId'] == 200][['timestamp', 'teamId', 'totalGold']]
    team200gold.rename(columns={"totalGold": "team200gold"}, inplace=True)

    golddiff = pd.merge(team100gold, team200gold, on='timestamp')
    golddiff['golddiff'] = golddiff['team100gold'] - golddiff['team200gold']

    golddiff['team100golddiff'] = [a if a > 0 else 0 for a in golddiff['golddiff']]
    golddiff['team200golddiff'] = [a if a < 0 else 0 for a in golddiff['golddiff']]

    return golddiff
