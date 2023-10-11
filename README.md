# OFFSHORE: Overly Friendly File System that Hides Obnoxious Redundant Errors

## Description

This is project aimed to developed an infrastructure to host a distributed File-System. The idea is to provide redundancies and speed on the upload or download of files stores in the remote servers. Besides that, even though the system was thought to run on separate computers, I also created a client CLI application able to communicate with the created protocols to provide the well-known feeling of a "Single Cloud Server". 

![A non-copyrighted AI generated logo for the project](assets/logo-1.png)

## Name suggestions
- Overly Friendly File System Sincerely that Honors Every Request Effortlessly (OFFSHORE).
- Our Filing Framework Seems Highly Optimistic, Rarely Encounters Glitches

## Preview

![Running Demo](assets/demo.gif)

## Running

As it is an example of a distributed computer program, each part of the program is supposed to run in a different node of a cluster. In order to simulate that behavior locally in a single computer, it was used Docker Compose to spawn different containers, each of them with a single module of the software.

The Docker Compose creates a simple internal network `11.56.1.0/24` and sets the Tracker Server at the address `11.56.1.21` arbitrarily. Besides that, it spawns three Seeder Nodes at the address `11.56.1.41`, `11.56.1.42`, `11.56.1.43`. As it is a Distributed Computing software, the number of Seeder Nodes can be as high as you can think, it is 3 by default to avoid spending too much local resources. Also, as each Seeder Node would have its own filesystem to really store the files, the docker compose solution to this is to create a `/disk` directory in the main operating system for each of the containers to use (All those directories are binded to the respective folders in the `.disks` directory).

It is easy to run it in a single command with Docker Compose. Assuming you have it installed (if you need any reference, take [this](https://www.youtube.com/watch?v=DM65_JyGxCo) video), just run the command to run the remote filesystem.

```
docker-compose up
```

With that up and running, just run the Client App in another terminal window by entering in the `client` directory, installing the required libraries placed on the `requirements.txt` file, and running it.

```
run.sh
```

You will be prompted with a `$` character supposed to be used as a prompt to your file system, just like you would with you were to use a linux terminal. You can be very free to use it, do not be scared of typing some undefined command and crashing the applications. It has built-in sintax error checking, so the only way to exit it is by typing `exit`.

You can access the main supported features by running the command `help`. But it is too much to ask, there are some functionalities already implemented.

- Upload files
- Download files

## Closing everything

To make sure that your group of docker applications and network has been properly finished, make sure to write the following command in the root directory of the project.

```
docker-compose down
```

Be smart, you can just `CTRL+C` your docker compose window and run it again. You will only need that command (As far as I am aware) if you want to take down the network interface created to host the group of containers.

## Architecture (BASICS)

Some basic information of how the system works. The project has 3 main modules: a **Tracker**, a **Seeder** and the **Client**. The remote filesystem is composed just by the Tracker and the Seeder while the Client applications is just a way of interacting with its protocols.

### Tracker

That module is reponsible to make sure what are the Seeders that are connected to the network, what files are availble for anyone to request and balance the files between the seeders in case one's connection might fail

### Seeder

That module is responsible for storing and uploading the files for anyone that may want it. It joins the network by first registering itself in the Tracker

### Client

As I said before, it is just a client application to replicate the linux terminal experience for anyone to interact with a working filesystem. All its configuration are binded to the docker environment used to test the whole thing in a single computer. It means that some configuration files and updates might be required to run it in a production environment (sure...).


![A nice AI generated GIF](assets/OFFSHORE.gif)
