# restro-comms

Nexmo log:
n) create app via cli: nexmo app:create; nexmo app:link. Can also be done from dashboard

Dev log:
1) Build NCCO object server on host/ncco

Deploy log:
1) create Heroku account and an app, download CLI
2) run heroku login
3) create heroku deployment files
4) run heroku git:remote --app booktwotables to init heroku remote
5) run git push heroku master to deployment
6) run heroku logs for logs to validate deployment and runtime errors
