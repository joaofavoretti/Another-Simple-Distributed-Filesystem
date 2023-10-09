# OFFSHORE: Overly Friendly File System that Hides Obnoxious Redundant Errors

## Description

This is a brand new idea I had to implement a distributed filesystem in a different way, derived from the first version accessible at [Simple Distributed Filesystem](https://github.com/joaofavoretti/Simple-Distributed-Filesystem).

It is not an updated version from the other repository, otherwise I would've used that repository. The idea is to build something related but with a different approach.

![Logo](assets/logo-1.png)

## Name suggestions
- Overly Friendly File System Sincerely that Honors Every Request Effortlessly (OFFSHORE).
- Our Filing Framework Seems Highly Optimistic, Rarely Encounters Glitches

## Running

As it is an example of a distributed computer program, each part of the program is supposed to run in a different node of a cluster. In order to simulate that behavior locally in a single computer, it was used Docker Compose to spawn different containers, each of them with a single module of the software.

The Docker Compose creates a simple internal network `11.56.1.0/24` and sets the Metadata Server at the address `11.56.1.21` arbitrarily. Besides that, it spawns three Storage Nodes at the address `11.56.1.41`, `11.56.1.42`, `11.56.1.43`. As it is a Distributed Systems software, the number of Storage Nodes can be as high as you can think, it is 3 by default to avoid spending too much resources locally. Also, as each Storage Node would have its own filesystem to really store the files, the docker compose solution to this is to create a directory in the main operating system for each of the containers to use (they are called: `storage-node-1`, `storage-node-2` and `storage-node-3`).

It is easy to run it in a single command with Docker Compose. Assuming you have it installed (if you need any reference, take [this](https://www.youtube.com/watch?v=DM65_JyGxCo) video), just run the command.

```
docker-compose up
```

With that up and running, just run the Client App in another terminal window by entering in the `client-app` directory, installing the required libraries placed on the `requirements.txt` file, and running it.

```
python3 client_app.py
```

You can also use the bash script `run.sh` in that same directory with the following command:

```
./run.sh
```

You will be prompted with a `>` character supposed to be used as a prompt to your file system, just like you would with you were to use a linux terminal. With that, you can type commands to used any of the implemented features it has, like:

- Upload files that you have locally to your remote filesystem
- Download files that you have uploaded to your computer
- List all the files that are on the filesystem
- `cat` the content of a file
- Remove a file that is on the filesystem

## Closing everything

To make sure that your group of docker applications and network has been properly finished, make sure to write the following command in the root directory of the project

```
docker-compose down
```

![Video](assets/OFFSHORE.gif)
