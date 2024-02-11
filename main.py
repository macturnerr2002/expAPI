
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)


from datetime import date
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import json
import re


## fixing the URLLIB3 Error
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
###### 
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


now = date.today() # current date


def getScheduleData():
    response = requests.get("https://www.windsorexpress.ca/sports/mbkb/2022-23/schedule",headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {}
        ## Should be a daily check every day at 00:00
        for div in soup.find_all("div", class_="list-group-item flex-fill text-center"):
            small_div = div.find("div", class_="small")
            if small_div:  # Check if the div was found
                key = small_div.get_text(strip=True).lower()
                h5_div = div.find("div", class_="h5")
                if h5_div:  # Check if the h5 div was found
                    value = h5_div.get_text(strip=True)
                    data[key] = value


        # Save data to a JSON file
        with open('./data/record_stats.json', 'w') as json_file:
            json.dump(data, json_file)
        print("Data extracted and saved to 'record_stats.json'.")  

        finished_games = []
        upcoming_games = []

        # Iterate over each game entry
        for game in soup.find_all("div", class_="event-row"):
            game_info = {}

            # Extract common game information
            date_info = game.find("div", class_="event-dateinfo")
            if date_info:
                game_info['date'] = date_info.get_text(strip=True)

            opponent_info = game.find("div", class_="event-opponent")
            if opponent_info:
                game_info['opponent'] = opponent_info.get_text(strip=True)

            # Determine if the game is finished or upcoming
            if "has-recap" in game.get('class', []):
                # Finished game
                result_info = game.find("div", class_="event-result")
                if result_info:
                    game_info['result'] = result_info.get_text(strip=True)
                finished_games.append(game_info)
            else:
                # Upcoming game
                upcoming_games.append(game_info)

        sched_res_Data = {
            "upcoming": upcoming_games,
            "finished": finished_games
        }

        with open ('./data/schedule_results.json', 'w') as json_file:
            json.dump(sched_res_Data, json_file)
        # Output the results
        print("Data extracted and saved to 'schedule_results.json'.") 
    else:
        print('ERROR LOADING: '+ str(response.status_code))       

def getRoster():
    response = requests.get("https://www.windsorexpress.ca/sports/mbkb/2023-24/teams/windsorexpress?sort=ptspg&view=lineup&pos=sh&r=0",headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        soup2 = soup.find(id='lineup')
        tables = soup2.find_all('table', class_='table')

        if tables and len(tables) >= 2:
            for j, table in enumerate(tables[:2]):  # Processing only the first two tables
                nheaders = [th.get_text(strip=True) for th in table.find_all('th')]

                data = []
                tbody = table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        row_data = {nheaders[i]: td.get_text(strip=True) for i, td in enumerate(row.find_all('td'))}
                        data.append(row_data)

                filename = f'./data/roster_{j+1}.json'  # Dynamic filename for each table
                with open(filename, 'w') as json_file:
                    json.dump(data, json_file)

                print(f"Data extracted and saved to '{filename}'.")
        

            
        else:
            print("Table not found in the HTML content.")
   
def teamStats():
    response = requests.get("https://windsorexpress2022.prestosports.com/sports/mbkb/2023-24/teams/windsorexpress?view=profile",headers=headers)
    if response.status_code == 200:
        #team stats first
        soup = BeautifulSoup(response.content, 'html.parser')


        team_stats = {}

        # Find all the rows in the table body
        rows = soup.find_all('tr')

        # Iterate through each row to extract the statistics
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                # Extract the name of the statistic
                stat_name = th.get_text(strip=True)
                # Extract the value of the statistic
                stat_value = td.get_text(strip=True)
                # Add the statistic and its value to the dictionary
                team_stats[stat_name] = stat_value

        with open ('./data/team_stats.json', 'w') as json_file:
            json.dump(team_stats, json_file)
        print("Data extracted and saved to 'team_stats.json'.") 

def getLeagueStandings():
    response = requests.get("https://stats-thebasketballleague.prestosports.com/sports/mbkb/2023-24/standings",headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        standings_table = soup.find('table', class_='table')  # Find the standings table
        standings = []
        for row in standings_table.find_all('tr')[2:]:  # Skip the header rows
            columns = row.find_all('td')
            team_name = row.find('th', class_='team-name').get_text(strip=True)
            
            # Conference and Overall Stats
            conf_gp, conf_wl, conf_pct, overall_gp, overall_wl, overall_pct = [col.get_text(strip=True) for col in columns]

            team_data = {
                'team': team_name,
                'conference': {
                    'games_played': conf_gp,
                    'win_loss': conf_wl,
                    'percentage': conf_pct
                },
                'overall': {
                    'games_played': overall_gp,
                    'win_loss': overall_wl,
                    'percentage': overall_pct
                }
            }
            standings.append(team_data)
        with open ('./data/league_standings.json', 'w') as json_file:
            json.dump(standings, json_file)
        print("Data extracted and saved to 'league_standings.json'.") 

    return standings

## Compiling

def format_date(date_str):
    date_str = re.sub(r"\(\w+\)", "", date_str).split()
    formatted_date = date_str[0] + " " + date_str[1]  # Format as 'month day'
    formatted_time = date_str[2] + " PM"  # Format as 'time PM'
    return formatted_date, formatted_time

def format_opponent(opponent_str):
    location = "AT" if "AT" in opponent_str else "VS"
    opponent_name = opponent_str.replace("AT", "").replace("VS", "").replace('*', '').strip()
    return location, opponent_name

def get_arena(location, opponent, static_data):
    if location == 'AT':
        return static_data['arenas'].get(opponent, "Unknown Arena")
    return "WFCU Centre"

def get_short_and_logo(opponent, static_data):
    return static_data["short"].get(opponent, "Unknown"), static_data["logos"].get(opponent, "Unknown")

def compileHome():
    home = {}

    # Read all data files at once
    with open('./data/admin.json', 'r') as file:
        admin_data = json.load(file)
    with open('./data/schedule_results.json', 'r') as file:
        schedule_results = json.load(file)
    with open('./data/static.json', 'r') as file:
        static_data = json.load(file)

    # Process header image
    home["header_image"] = admin_data["view"]["header_image"]

    # Process next game
    next_game = schedule_results['upcoming'][0]
    date, time = format_date(next_game['date'])
    location, opponent_name = format_opponent(next_game['opponent'])
    arena = get_arena(location, opponent_name, static_data)
    _, opponent_logo = get_short_and_logo(opponent_name, static_data)
    title = f"EXPRESS {location} {opponent_name.split(' ')[1].upper()}"
    
    home["next_game"] = {
        "Date": date,
        "Time": time,
        "Opponent": opponent_name,
        "Location": location,
        "Arena": arena,
        "Title": title,
        "Logo": opponent_logo
    }

    # Process upcoming games
    for i, match in enumerate(schedule_results["upcoming"][1:3], start=1):
        date, _ = format_date(match['date'])
        location, opponent = format_opponent(match['opponent'])
        short, logo = get_short_and_logo(opponent, static_data)
        home[f"upcoming_game{i}"] = {
            "date": date,
            "location": location,
            "opponent": opponent,
            "abbreviation": short,
            "logo_path": logo
        }

    # Process finished games
    for i, match in enumerate(schedule_results["finished"][-2:], start=1):
        date, _ = format_date(match['date'])
        location, opponent = format_opponent(match['opponent'])
        short, logo = get_short_and_logo(opponent, static_data)
        result, score = match["result"].split(',')
        home[f"finished_game{i}"] = {
            "date": date,
            "location": location,
            "opponent": opponent,
            "abbreviation": short,
            "logo_path": logo,
            "score": score.strip(),
            "result": result
        }

    return home

def compileTeam():
    team_data = {}

    # Assuming 'league_standings.json' contains the standings data
    with open('./data/league_standings.json', 'r') as file:
        standings_data = json.load(file)

    # Assuming 'team_stats.json' contains the stats data
    with open('./data/team_stats.json', 'r') as file:
        stat_data = json.load(file)

    # Assuming 'roster.json' contains the stats data
    with open('./data/roster_1.json', 'r') as file:
        player_stats = json.load(file)
    
    with open('./data/roster_2.json', 'r') as file:
        player_stats2 = json.load(file)

    # Find the Windsor Express data in standings
    place = 1
    for rank in standings_data:
        if rank['team'] == "Windsor Express":
            break
        else:
            place += 1

        

    # Extract relevant stats from team stats
    windsor_stats = stat_data
    team_data['record_stats'] = {
        'standing': place,
        'overall': windsor_stats['Overall'].split(' ')[0],
        'games': windsor_stats['Games'],
        'ppg': windsor_stats['Points per game'],
        'fgp': windsor_stats['FG Pct']
    }


    for player in player_stats:
        player['ppg'] = float(player['ppg'].replace('\r\n', ' ').strip()) if player['ppg'] else 0

    # Sorting the players by 'ppg'
    sorted_players = sorted(player_stats, key=lambda x: x['ppg'], reverse=True)
    topPPG = sorted_players[0]
    topPPG['Name'] = topPPG['Name'].replace('\r\n        ',' ')

    sorted_players2 = sorted(player_stats2, key=lambda x: x['reb/g'], reverse=True)
    topRPG = sorted_players2[0]
    topRPG['Name'] = topRPG['Name'].replace('\r\n        ',' ')

    sorted_players2 = sorted(player_stats2, key=lambda x: x['ast/g'], reverse=True)
    topAST = sorted_players2[0]
    topAST['Name'] = topAST['Name'].replace('\r\n        ',' ')

    team_data['leaders'] = {
        "ppg": {
            "name": topPPG['Name'].upper(),
            "number": topPPG['#'],
            "position": topPPG['Pos'],
            "stat": topPPG['ppg']
        },
        "rpg": {
            "name": topRPG['Name'].upper(),
            "number": topRPG['#'],
            "position": topRPG['Pos'],
            "stat": topRPG['reb/g']
        },
        "ast": {
            "name": topAST['Name'].upper(),
            "number": topAST['#'],
            "position": topAST['Pos'],
            "stat": topAST['ast/g']
        }
    }


    with open('./data/roster_1.json', 'r') as file:
        roster = json.load(file)

    # Extract and format player data
    formatted_roster = []
    for player in roster:
        player_data = {
            "name": player["Name"].strip().replace('\r\n', ' '),  # Clean up the name field
            "number": player["#"],
            "position": player["Pos"]
        }
        formatted_roster.append(player_data)

    # Add roster string to team data
    team_data["roster"] = formatted_roster

    

    return team_data

def saveFile():
    dataObj = {
        "home": compileHome(),
        "team": compileTeam()
    }
    with open('./data/compiled.json', 'w') as json_file:
         json.dump(dataObj, json_file)



def fetch_data():
    getScheduleData()
    getRoster()
    teamStats()
    getLeagueStandings()
    saveFile()

scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_data, trigger="interval", minutes=5)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/data', methods=['GET'])
def get_data():
    try:
        with open('./data/compiled.json', 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/fetch', methods=['GET'])
def forced_Fetch():
    fetch_data()
    try:
        with open('./data/compiled.json', 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=80)







