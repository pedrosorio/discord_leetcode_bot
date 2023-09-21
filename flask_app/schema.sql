-- drop all tables and create them again with indexes

DROP TABLE IF EXISTS server_to_channel;
DROP TABLE IF EXISTS discord_users;
DROP TABLE IF EXISTS server_users; 
DROP TABLE IF EXISTS contests;
DROP TABLE IF EXISTS contest_performances;

CREATE TABLE server_to_channel(
    server_id int PRIMARY KEY,
    channel_id int,
    custom_message text
);

CREATE TABLE discord_users(
    discord_user_id int PRIMARY KEY,
    discord_username
);

CREATE TABLE server_users(
    server_id int,
    discord_user_id int,
    leetcode_username text,
    UNIQUE(server_id, discord_user_id)
);

CREATE TABLE contests(
    contest_name text PRIMARY KEY,
    timestamp int 
);

CREATE TABLE contest_performances(
    contest_name text,
    leetcode_username text,
    rank int,
    new_rating float,
    delta_rating float,
    country_code text,
    UNIQUE(contest_name, leetcode_username)
);