// MongoDB initialization script for EarnORM
// This script creates the database and user for EarnORM testing

// Switch to the earnbase database
db = db.getSiblingDB('earnbase');

// Create a user for the earnbase database
db.createUser({
  user: 'earnorm_user',
  pwd: 'earnorm_pass',
  roles: [
    {
      role: 'readWrite',
      db: 'earnbase'
    }
  ]
});

// Create collections with some initial setup
db.createCollection('user');
db.createCollection('post');
db.createCollection('department');
db.createCollection('employee');

// Create indexes for better performance
db.user.createIndex({ "email": 1 }, { unique: true });
db.user.createIndex({ "name": 1 });
db.user.createIndex({ "age": 1 });
db.user.createIndex({ "is_active": 1 });

db.post.createIndex({ "author": 1 });
db.post.createIndex({ "title": 1 });

db.department.createIndex({ "code": 1 }, { unique: true });
db.department.createIndex({ "name": 1 });

db.employee.createIndex({ "email": 1 }, { unique: true });
db.employee.createIndex({ "department": 1 });

print('EarnORM database initialized successfully!');
