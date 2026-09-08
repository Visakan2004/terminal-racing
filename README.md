# 🏎️ Terminal Racing

An arcade-style racing game that runs entirely inside your Linux terminal using text/ASCII graphics, packaged into an ultra-lightweight Docker container.

```
╔════════════════════════════════════════════════════════╗
║                ═══ TERMINAL RACING ═══                 ║
║                                ╔══════════════════╗    ║
║     ║        │   .T.  │        ║  ║  DASHBOARD    ║    ║
║     ║        │  |TXI| │        ║  ╠════════════════╣   ║
║     ║        │  '-=-' │        ║  ║ Score: 1420   ║    ║
║     ║  /V\   │        │        ║  ║ Best:  2580   ║    ║
║     ║ |[X]|  │        │        ║  ║ Lives: ♥ ♥ ♥  ║    ║
║     ║ d---b  │        │        ║  ║ Speed: 110km/h║    ║
║     ║        │        │   .-.  ║  ║ Level: 3      ║    ║
║     ║        │        │  |[1]| ║  ║ Passed: 18    ║    ║
║     ║        │  /^\   │  '-=-' ║  ╚════════════════╝    ║
║     ║        │ |[P]|  │        ║                       ║
║     ║        │ d---b  │        ║                       ║
╚════════════════════════════════════════════════════════╝
```

---

## 📖 1. Project Description

**Terminal Racing** is a fast-paced retro racing game developed in Python 3. It runs directly inside any standard terminal using `curses` for high-performance terminal rendering, zero-latency keyboard input, and vibrant 256-color ASCII graphics.

As the driver, your goal is to navigate highway traffic, overtake enemy vehicles, dodge sudden hazards, and survive as your speed continuously accelerates!

---

## ✨ 2. Features

- **🎮 Smooth Arcade Gameplay**: Responsive steering with multi-lane traffic navigation.
- **🎨 Rich Terminal Graphics**: Custom ASCII car models (sedans, racers, trucks, and taxis) with animated road markings and roadside scenery.
- **🚥 Fair Traffic Algorithm**: Smart enemy spawning that prevents impossible roadblocks, always giving skilled players a viable escape path.
- **💥 Crash & Recovery System**: Visual crash animation (`*BOOM*`) with a 3-life system and momentary respawn grace period.
- **📈 Progressive Difficulty**: Game speed ramps up dynamically from 60 km/h to over 220 km/h as your score increases.
- **🏆 Persistent High Score**: Automatically tracks and saves your best records to disk.
- **⏸️ Pause & Resume**: Pause anytime during intense runs.
- **📐 Responsive Terminal Handling**: Gracefully detects terminal dimensions and prompts you if the window needs resizing.
- **🐳 100% Dockerized**: Zero setup required—runs anywhere Docker is installed with one simple command.

---

## 📋 3. Requirements

You **only** need:
- [Docker](https://www.docker.com/) installed on your machine (Linux, macOS, or Windows with WSL2).

> [!NOTE]
> You **do not** need to install Python, `pip`, or any local system libraries on your host machine. Docker handles the entire environment automatically!

---

## 🔨 4. Build the Docker Image

To build the Docker image locally, navigate to the project directory in your terminal and run:

```bash
docker build -t terminal-racing .
```

This compiles the lightweight container image (based on official `python:3.12-slim`), configures terminal color variables, and sets up a secure non-root runtime user.

---

## 🚀 5. Run the Game

Launch the game with an interactive terminal session:

```bash
docker run -it --rm terminal-racing
```

### Explanation of Docker flags:
- `-i` (**Interactive**): Keeps standard input (`STDIN`) open so your keystrokes are received by the game.
- `-t` (**TTY**): Allocates a pseudo-terminal, which enables `curses` to read arrow keys and render colors.
- `--rm` (**Remove**): Automatically cleans up and removes the container when the game exits.

---

## 💾 6. Exporting and Loading Image Files (.tar)

If you need the Docker image as a standalone file to share without rebuilding:

### Export Image to a File:
```bash
docker save -o terminal-racing-image.tar terminal-racing:latest
```

### Load Image from File (on any machine with Docker):
```bash
docker load -i terminal-racing-image.tar
```

---

## ☁️ 7. Push Image to Docker Hub (or Container Registry)

To push your image to Docker Hub so anyone can pull and play:

1. **Log in to Docker Hub**:
   ```bash
   docker login
   ```

2. **Tag the image with your Docker Hub username**:
   ```bash
   docker tag terminal-racing:latest <your-dockerhub-username>/terminal-racing:latest
   ```

3. **Push to Docker Hub**:
   ```bash
   docker push <your-dockerhub-username>/terminal-racing:latest
   ```

4. **Anyone can now pull and run it with**:
   ```bash
   docker run -it --rm <your-dockerhub-username>/terminal-racing:latest
   ```

---

## 🎮 8. Game Controls

| Key | Action |
| :--- | :--- |
| <kbd>←</kbd> or <kbd>A</kbd> or <kbd>H</kbd> | Steer Left |
| <kbd>→</kbd> or <kbd>D</kbd> or <kbd>L</kbd> | Steer Right |
| <kbd>P</kbd> | Pause / Resume game |
| <kbd>Space</kbd> / <kbd>Enter</kbd> | Start Game (from Title Screen) |
| <kbd>R</kbd> | Restart game (after Game Over) |
| <kbd>Q</kbd> or <kbd>Esc</kbd> | Quit game |

---

## 💡 9. How Docker Solves the Environment Problem

When sharing a terminal game built in Python with another person, common issues often arise:
1. **Missing or Incompatible Python Versions**: The target machine might have an older Python version without necessary language features.
2. **Platform & Library Differences**: The standard `curses` library behaves differently across Windows, macOS, and Linux distributions, often requiring platform-specific binaries or system packages like `ncurses-term`.
3. **Terminal Encoding & Character Issues**: Different operating systems default to varying terminal encodings, which can corrupt ASCII art and borders.

### The Docker Solution:
Docker packages the application together with its exact Linux runtime environment:
- **Consistent Python 3.12 Linux Runtime**: Eliminates the "it works on my machine" problem.
- **Standardized Terminal Settings**: The Dockerfile configures `TERM=xterm-256color` and `LANG=C.UTF-8` so colors and borders render identically on all host platforms.
- **Zero Host Pollution**: No dependencies are installed on the user's host system; running `docker run -it --rm terminal-racing` just works instantly out-of-the-box.

---

## 📁 10. Project Structure

```text
terminal-racing/
├── game.py            # Complete game engine, physics, collision detection & curses UI
├── Dockerfile         # Lightweight Linux container definition & environment config
├── .dockerignore      # Prevents cache, git, and local temporary files from entering the image
├── requirements.txt   # Dependencies documentation (Python 3 standard library)
└── README.md          # Complete project guide and Docker learning documentation
```

### File Details:
- **`game.py`**: Contains the core game loop, input handling, sprite definitions, collision math, difficulty scaling, and high score manager.
- **`Dockerfile`**: Builds a minimal `python:3.12-slim` image, configures `TERM` & `LANG`, creates a non-root `gamer` user, and sets the automatic entrypoint.
- **`.dockerignore`**: Excludes build artifacts (`__pycache__`), virtual environments, and `.git` from the Docker build context.
- **`requirements.txt`**: Documents dependencies for the project.
- **`README.md`**: Beginner-friendly guide explaining how the game and Docker integration work.

---

## 🏁 Enjoy the Race!

Have fun weaving through traffic and setting new high scores! 🚗💨
