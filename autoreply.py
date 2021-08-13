import tweepy
import logging
from config import create_api
import time
import os
import json
import subprocess
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def check_mentions(api, since_id):
    logger.info("Recibiendo menciones...")
    new_since_id = since_id
    for tweet in tweepy.Cursor(api.mentions_timeline, tweet_mode="extended",  since_id=since_id).items():
        new_since_id = max(str(tweet.id), new_since_id)
        
        #if tweet.in_reply_to_status_id is not None:
        #    continue        
        logger.info("Respondiendo a {name}".format(name=tweet.user.name))
        
        text = re.sub("@[a-zA-Z0-9]+", " ", tweet.full_text, flags=re.I)
        
        if ';' in text or '{' in text or '(' in text or '+' in text or '"' in text:
            response = evaluateJs(str(tweet.id),text)
        else:
            response = "Hola, puedes executar Javascript llamandome!"
         
        api.update_status(status=response,in_reply_to_status_id=tweet.id,auto_populate_reply_metadata=True)

        try:
          if not tweet.user.following:
            tweet.user.follow()
        except:
          pass
        
               
    return new_since_id

def evaluateJs(tweet_id, text):
    config_accesskey = os.environ['AWS_ACCESS_KEY']
    config_secret = os.environ['AWS_ACCESS_SECRET']
    config_region = os.environ['AWS_REGION']
    default_aws_access_config = "AWS_ACCESS_KEY_ID={config_accesskey} AWS_SECRET_ACCESS_KEY={config_secret} AWS_DEFAULT_REGION={config_region}".format(config_accesskey=config_accesskey,config_secret=config_secret,config_region=config_region)
    
    text = text.replace("\n", " ").replace('"', '\\"').replace('&gt;', '>').replace('&lt;', '<')

    #content = '''exports.handler = async (event) => {
    #    ret = eval("[CODE]");
    #    return ret;
    #  };'''
    #content = content.replace('[CODE]', text)
    
    content = text

    with open("/tmp/jsuno/script_" + tweet_id + ".js", "w") as wf:
        wf.write(content)
    

    ret = system_call("{default_aws_access_config} aws s3 cp /tmp/jsuno/script_{tweet_id}.js s3://jsuno/script_{tweet_id}.js".format(default_aws_access_config=default_aws_access_config,tweet_id=tweet_id))

    #os.system("rm /tmp/jsuno.zip")
    #os.system("zip /tmp/jsuno.zip -j /tmp/jsuno/index.js")
    #ret = system_call("{default_aws_access_config} aws lambda update-function-code --function-name jsuno --zip-file fileb:///tmp/jsuno.zip".format(default_aws_access_config=default_aws_access_config))

    #if "error" in str(ret):
    #    return "Tuvimos un error al ejecutar. Por favor intenta luego!"
    #else:
    if True:
        ret = os.system("{default_aws_access_config} aws lambda invoke --function-name \"jsuno:\$LATEST\" --payload '{{\"filename\": \"script_{tweet_id}.js\"}}' \"/tmp/jsuno/out_{tweet_id}.txt\"".format(default_aws_access_config=default_aws_access_config, tweet_id=tweet_id))
  
        result = ""
        with open("/tmp/jsuno/out_" + tweet_id + ".txt", "r") as f:
            result = str(f.read())
        
        if "{" in result:
          response = json.loads(result)
          status = 'Success' if 'errorMessage' not in response else response['errorMessage']
        else:
          status = result

        return status

def system_call(command):
    try:
        return str(subprocess.check_output([command], shell=True, stderr=subprocess.STDOUT))
    except subprocess.CalledProcessError as e:
        return str(e.output)

def main():
    api = create_api()
    since_id = "1"
    lastid_file = "/home/ubuntu/javascriptbot/last_id.txt"
    with open(lastid_file, "r") as f:
        since_id = str(f.read())
    
    since_id = check_mentions(api, since_id)
    
    with open(lastid_file, "w") as wf:
        wf.write(since_id)

if __name__ == "__main__":
    main()
