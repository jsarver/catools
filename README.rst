Soap Helper Library for CA Service Desk

Features
Create and update any Object
Create and update tickets
Create and contacts

Usage:
#creating a client that interfaces with CA
client = login("hostname", "username", "password")

#Now you can perform several tasks
results = client.searchObjects("cnt","last_name='smith'",-1, ["last_name","first_name"])
#print list of users
for user in results.to_dict():
    print(user['last_name'], user['first_name']


#Update an object
#query for users named smith and asking to only return the last_name and first_name attributes
results = client.searchObjects("cnt", "last_name='smith'",-1, ["last_name","first_name"])

#pick first user from search
user = results[0]
#change users first name to ned
c.updateObject(user['handle'], ["first_name","ned"], ["first_name","last_name"])

#list attributes for an object
print(client.listAttributes('cnt'))

