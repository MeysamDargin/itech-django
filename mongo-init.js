// Create the itech database if it doesn't exist
db = db.getSiblingDB('iTech');

// Create a user for the itech database
db.createUser({
  user: 'mongo_user',
  pwd: 'mongo_password',
  roles: [
    {
      role: 'readWrite',
      db: 'iTech'
    }
  ]
});

// Create some initial collections
db.createCollection('profiles');
db.createCollection('logs');

// Add some metadata
db.metadata.insertOne({
  name: 'iTech Database',
  version: '1.0',
  created_at: new Date()
}); 