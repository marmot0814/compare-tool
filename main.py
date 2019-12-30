import os
import datetime
import subprocess
from argparse import ArgumentParser
import json
import time


def main():
    ScoreBoard(Config(Parser().config).json)

class Config:
    def __init__(self, config_filename):
        with open(config_filename, 'r') as config_file:
            self.json = json.load(config_file);
        self.json["github_repo_name"] = self.json["github_repo_remote_path"].replace('/', ' ').replace('.', ' ').split()[-2]
        self.json["path"] = self.json["github_repo_name"] + self.json["github_repo_local_path"]
        
def Parser():
    parser = ArgumentParser()
    parser.add_argument("--config", help="Your Config File", default="config.json");
    return parser.parse_args()



class ScoreBoard:
    def __init__(self, config):
        self.config = config;
        self.prev_HEAD_hash = ""
        while True:
            self.update_github_repo()
            self.generate_scoreboard()
            time.sleep(60)
        
    def update_github_repo(self):
        if os.path.isdir(self.config["github_repo_name"]):
            proc = subprocess.run(['git', 'pull'], cwd=self.config["github_repo_name"])
            if not proc.returncode:
                return 
            subprocess.run(['rm', '-r', self.config['github_repo_name']])
            self.prev_HEAD_hash = ""
        subprocess.run(['git', 'clone', self.config['github_repo_remote_path']])
        
    def get_HEAD_hash(self):
        proc = subprocess.Popen(['git', 'rev-parse', 'HEAD'], cwd=self.config["github_repo_name"], stdout=subprocess.PIPE)
        return proc.stdout.readline()

    def have_change(self):
        return self.prev_HEAD_hash != self.get_HEAD_hash()

    def get_users(self):
        output_path = os.path.join(self.config["path"], "output")
        return [user for user in os.listdir(output_path) if os.path.isdir(os.path.join(output_path, user))]

    def get_testcases(self):
        input_path = os.path.join(self.config["path"], "input")
        return [testcase for testcase in os.listdir(input_path) if os.path.isdir(os.path.join(input_path, testcase))]

    def output_html(self, html):
        with open(self.config["scoreboard_filename"], "w") as output:
            output.write(html)
    
    def compare(self, testcase_id, a, b):
        proc = subprocess.Popen(['diff', 
            os.path.join(
                self.config['path'], 
                'output', 
                self.users[a], 
                self.testcases[testcase_id]
            ), 
            os.path.join(
                self.config['path'],
                'output',
                self.users[b],
                self.testcases[testcase_id]
            )
        ], stdout=subprocess.PIPE)
        s = proc.stdout.readline()
        return len(s) == 0


    def gen_users_results(self):
        users_results = [[0 for testcase in self.testcases] for user in self.users]
        for testcase_id in range(len(self.testcases)):
            pool = []
            for user_id in range(len(self.users)):
                if not os.path.exists(os.path.join(self.config["path"], "output", self.users[user_id], self.testcases[testcase_id])):
                    continue
                result = len(pool)
                for it in range(result):
                    if self.compare(testcase_id, pool[it], user_id):
                        result = it
                        break
                if result == len(pool):
                    pool.append(user_id)
                users_results[user_id][testcase_id] = result + 1

        return users_results

    def generate_scoreboard(self):
        if not self.have_change():
            return
        self.prev_HEAD_hash = self.get_HEAD_hash()
        self.testcases = self.get_testcases()
        self.users = self.get_users()
        self.users_results = self.gen_users_results()
        self.output_html(self.html())

    def html(self):
        html = '''
<!DOCTYPE html>
<html lang="en">
{0}
{1}
</html>
               '''
        return html.format(self.head(), self.body())
    
    def head(self):
        html = '''
<head>
<!-- Required meta tags -->
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta http-equiv="content-language" content="English">
<meta name="viewport" content="width=device-width, initial-scale=1.0, shrink-to-fit=yes">
<meta name="keywords" content="Compiler, NCTU">
<meta name="discription" content="">
<!-- title -->
<title>{0}</title>
<link rel="icon" type="image/png" href="https://lh3.googleusercontent.com/3txMoTdolI_JziAIDnOQuki1JeEbHXsGnMW-XdvxqL63cuYYqxrbwJ8VsL2jH5gjRdM-=w300">
<!-- Bootstrap CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta/css/bootstrap.min.css" integrity="sha384-/Y6pD6FV/Vv2HJnA6t+vslU6fwYXjCFtcEpHbNJ0lyAFsXTsjBbfaDjzALeQsN6M" crossorigin="anonymous">
</head>
               '''
        return html.format(self.config['title'])

    def body(self):
        html = '''
<body>
<div class="container">
{0}
</div>
</body>
               '''
        return html.format(self.table())
    
    def table(self):
        html = '''
<table class="table table-hover table-bordered">
{0}
{1}
{2}
</table>
               '''
        return html.format(self.caption(), self.thead(), self.tbody())

    def caption(self):
        html = '''
<caption class="text-center" style="caption-side: top">
<h2 style="color: #000000;">{0}</h2>
</caption>
<caption class="text-right" style="caption-side: bottom">
<em><small>Generated at {1}</small></em>
</caption>
               '''
        return html.format(self.config['title'], datetime.datetime.now())

    def thead(self):
        html = '''
<thead>
<tr>
{0}
</tr>
</thead>
               '''
        return html.format(
            "<th class=\"text-center\">User Name</th>\n" +
            '\n'.join(map(str, [
                "<th class=\"text-center\">{0}</th>".format(testcase) for testcase in self.testcases
            ]))
        )

    def tbody(self):
        html = '''
<tbody>
{0}
</tbody>
               '''
        return html.format(
            '\n'.join(map(str, [ "<tr>{0}</tr>".format(
                "<td class=\"text-center\">{0}</td>\n".format(self.users[user_id]) + 
                '\n'.join(map(str, [
                    "<td class=\"text-center\" style=\"background-color: {0}\"></td>".format(self.config["color"][result]) for result in self.users_results[user_id]
                ]))
            ) for user_id in range(len(self.users)) ]))
        )

if __name__ == '__main__':
    main()
