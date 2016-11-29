#!/usr/bin/env python
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from datetime import datetime
import os
import json
from auth import TwitterAuth

# Output directory to hold json files (one per day) with tweets
# Within the output directory, the script loads a file named FILTER with the terms to be tracked (one per line)

outputDir = "data"

## End of Settings###

class FileDumperListener(StreamListener):

    def __init__(self,filepath):
        super(FileDumperListener,self).__init__(self)
        self.basePath=filepath
        os.system("mkdir -p %s"%(filepath))

        d=datetime.today()
        self.filename = "%i-%02d-%02d-1.json"%(d.year,d.month,d.day)        
        self.fh = open(self.basePath + "/" + self.filename,"a")#open for appending just in case
        
        self.tweetCount=0
        self.errorCount=0
        self.limitCount=0
        self.last=datetime.now()
    
    #This function gets called every time a new tweet is received on the stream
    def on_data(self, data):
    #Twitter returns data in JSON format - we need to decode it first
        decoded = json.loads(data)
        if  not decoded['text'].startswith('RT'):
            #Do processing here
            self.fh.write(data)
            self.tweetCount+=1


        #Status method prints out vitals every five minutes and also rotates the log if needed
        self.status()
        return True
        
    def close(self):
        try:
            self.fh.close()
        except:
            #Log/email
            pass
    
    #Rotate the log file if needed.
    #Warning: Check for log rotation only occurs when a tweet is received and not more than once every five minutes.
    #         This means the log file could have tweets from a neighboring period (especially for sparse streams)
    def rotateFiles(self):
        d=datetime.today()
        filenow = "%i-%02d-%02d-1.json"%(d.year,d.month,d.day)
        if (self.filename!=filenow):
            print("%s - Rotating log file. Old: %s New: %s"%(datetime.now(),self.filename,filenow))
            try:
                self.fh.close()
            except:
                #Log/Email it
                pass
            self.filename=filenow
            self.fh = open(self.basePath + "/" + self.filename,"a")

    def on_error(self, statusCode):
        print("%s - ERROR with status code %s"%(datetime.now(),statusCode))
        self.errorCount+=1
    
    def on_timeout(self):
        raise TimeoutException()
    
    def on_limit(self, track):
        print("%s - LIMIT message recieved %s"%(datetime.now(),track))
        self.limitCount+=1
    
    def status(self):
        now=datetime.now()
        if (now-self.last).total_seconds()>300:
            print("%s - %i tweets, %i limits, %i errors in previous five minutes."%(now,self.tweetCount,self.limitCount,self.errorCount))
            self.tweetCount=0
            self.limitCount=0
            self.errorCount=0
            self.last=now
            self.rotateFiles()#Check if file rotation is needed
        

class TimeoutException(Exception):
    pass

if __name__ == '__main__':
    while True:
        try:
            #Create the listener
            listener = FileDumperListener(outputDir)
            auth = OAuthHandler(TwitterAuth.consumer_key, TwitterAuth.consumer_secret)
            auth.set_access_token(TwitterAuth.access_token, TwitterAuth.access_token_secret)
            fhTerms = open(outputDir+"/FILTER","r")
            terms=[]
            for line in fhTerms:
                terms.append(line.decode('utf-8').strip())
            print("%s - Starting stream to track %s"%(datetime.now(),",".join(terms)))
            #Connect to the Twitter stream
            stream = Stream(auth, listener)
            stream.filter(track=terms, languages=['en'])

        except KeyboardInterrupt:
            #User pressed ctrl+c or cmd+c -- get ready to exit the program
            print("%s - KeyboardInterrupt caught. Closing = and exiting."%datetime.now())
            listener.close()
            stream.disconnect()
            break
        except TimeoutException:
            #Timeout error, network problems? reconnect.
            print("%s - Timeout exception caught. Closing stream and reopening."%datetime.now())
            try:
                listener.close()
                stream.disconnect()
            except:
                pass
            continue
