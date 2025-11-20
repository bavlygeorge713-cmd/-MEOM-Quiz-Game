# MEOM Quiz Game

A professional desktop quiz game application designed for educational competitions, featuring real-time gameplay, team management, and an intuitive admin panel.

## Features

### Game Mechanics
- **Multi-team Support**: 2-4 teams competing simultaneously
- **Dynamic Wheel System**: Randomized team selection for fair gameplay
- **Timed Questions**: Configurable countdown timer (10-120 seconds)
- **Tiebreaker Mode**: Special golden question for tied scores
- **Real-time Scoring**: Live score updates with visual feedback

### User Interface
- **Player Window**: Full-screen immersive game experience
- **Admin Panel**: Comprehensive control center for game management
- **Visual Feedback**: Color-coded answers, team highlights, and animations
- **Responsive Design**: Adaptive layouts for different screen sizes
- **Sound Effects**: Audio cues for correct/wrong answers and victory

### Administration
- **Question Management**: Add, edit, and delete questions on-the-fly
- **Import/Export**: JSON-based question bank management
- **Live Settings**: Adjust teams, scoring, and timing during gameplay
- **Manual Controls**: Override wheel results and set custom scores
- **Password Protection**: Secure admin access (default password: 250595)

## Installation

### Pre-built Executable (Recommended)

1. Download the latest release from the Releases page
2. Extract the ZIP file to your desired location
3. Run `MEOM_Quiz_Game.exe` (Windows) or equivalent for your platform

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/meom-quiz-game.git
cd meom-quiz-game

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python quiz_admin_player_main.py
```

## Quick Start

1. **Launch the application** - Player Window opens automatically in fullscreen
2. **Access Admin Panel** - Click the "Admin Panel" button in the top-right corner and enter password (default: `250595`)
3. **Configure Settings** - Navigate to Settings tab and set team names, timer duration, and scoring rules
4. **Start Game** - Click "SPIN WHEEL TO START" in the Player Window
5. **Play** - Select question numbers to display questions and begin gameplay

## Game Rules

### Basic Gameplay

1. **Team Selection**: Spin the wheel once at game start to determine the first team
2. **Round-Robin Rotation**: Teams alternate after each question
3. **Question Selection**: Active team clicks a number (1-25) to reveal a question
4. **Answer Submission**: Team has the configured time (default 30s) to select an answer
5. **Scoring**: 
   - Correct answer: +2 points (configurable)
   - Wrong answer: 0 points (configurable: -5 to +5)
   - Timeout: 0 points, question marked as skipped

### Tiebreaker Rules

When all regular questions are answered and the top score is shared by multiple teams:
- A TIEBREAKER question appears (golden card)
- Teams continue rotating until someone answers correctly
- First team to answer correctly wins the game
- Wrong answers rotate to the next team

### Visual Indicators

- **Blue Card**: Unanswered question
- **Green Card**: Correctly answered (with team color)
- **Red Card**: Incorrectly answered (with team color)
- **Gray Card**: Timed out / skipped
- **Gold Card**: Tiebreaker question
- **Golden Outline**: Current active team

## Admin Panel Guide

### Dashboard Tab
- View game statistics (total questions, remaining, current team, status)
- Monitor team scores in real-time
- Quick actions: Force start, reset game, open player window
- Export/import questions

### Questions Tab
- **Add Question**: Click "Add Question" button, enter text and 4 options, select correct answer
- **Edit Question**: Click "Edit" on any question to modify it
- **Delete Question**: Click "Delete" (not available for tiebreaker question)
- Questions show color feedback after being answered (green for correct, red for wrong)

### Settings Tab
- **Team Configuration**: Set number of teams (2-4) and custom team names
- **Timer Duration**: Set question timer (10-120 seconds)
- **Scoring Rules**: Points for correct answers (default: 2) and wrong answers (default: 0)
- Click "Save Settings" to apply changes

### Game Control Tab
- **Wheel Controls**: Manually set which team starts if needed
- **Score Override**: Manually adjust team scores for corrections

## Question Format

Questions are stored in JSON format:

```json
[
  {
    "id": 0,
    "question": "What is the average blink rate per minute?",
    "options": ["5-10", "15-20", "25-30", "35-40"],
    "correct": 1
  },
  {
    "id": 1,
    "question": "Which cranial nerve innervates the lateral rectus muscle?",
    "options": ["CN III", "CN IV", "CN V", "CN VI"],
    "correct": 3
  }
]
```

**Field Descriptions:**
- `id`: Unique question identifier (0-indexed)
- `question`: Question text (supports Unicode and emojis)
- `options`: Array of exactly 4 answer choices
- `correct`: Index of correct answer (0-3, where 0=A, 1=B, 2=C, 3=D)

**Note**: The last question in the array is automatically designated as the tiebreaker question.

## Configuration

### Change Admin Password

Edit `quiz_admin_player_main.py`:

```python
ADMIN_PASSWORD = "your_new_password"
```

### Modify Default Settings

Edit the `Settings` class in `quiz_admin_player_main.py`:

```python
@dataclass
class Settings:
    team1_name: str = "Team 1"
    team2_name: str = "Team 2"
    timer_duration: int = 30  # seconds
    points_correct: int = 2
    points_wrong: int = 0
    number_of_teams: int = 2
```

## Building from Source

### Prerequisites

```bash
pip install pyinstaller pywebview
```

### Build Executable

**Windows:**
```bash
pyinstaller --name="MEOM_Quiz_Game" --windowed --onefile --add-data="web;web" --add-data="sounds;sounds" quiz_admin_player_main.py
```

**macOS:**
```bash
pyinstaller --name="MEOM_Quiz_Game" --windowed --onefile --add-data="web:web" --add-data="sounds:sounds" quiz_admin_player_main.py
```

**Linux:**
```bash
pyinstaller --name="MEOM_Quiz_Game" --onefile --add-data="web:web" --add-data="sounds:sounds" quiz_admin_player_main.py
```

The executable will be in the `dist/` folder.

## Troubleshooting

### Common Issues

**Admin Panel button not responding**
- Ensure password is correct (default: `250595`)
- Check browser console for JavaScript errors

**Questions not loading**
- Verify JSON format is correct
- Check that last question is marked as tiebreaker

**Player window not opening from Admin Panel**
- Close any existing player windows first
- Restart the application

**Tiebreaker not appearing**
- Ensure all regular questions are answered
- Verify at least 2 teams have the same top score

**Audio not playing**
- Check that sound files exist in `sounds/` directory
- Verify file paths match HTML references

### Enable Debug Mode

Run with debug output:

```python
# In quiz_admin_player_main.py, change line 856:
webview.start(debug=True)
```

## Project Structure

```
meom-quiz-game/
├── quiz_admin_player_main.py    # Main application file
├── web/
│   ├── admin.html               # Admin panel interface
│   └── player.html              # Player window interface
├── sounds/
│   ├── correct_sound/
│   │   └── correct_sound.mp3
│   ├── wrong_sound/
│   │   └── wrong_sound.mp3
│   ├── ticking_sound/
│   │   └── ticking_sound.mp3
│   └── victory_sound/
│       └── victory_sound.wav
├── requirements.txt
├── README.md
└── LICENSE
```

## Requirements

- **Python**: 3.8 or higher
- **Dependencies**: 
  - pywebview >= 4.0.0
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 20.04+)
- **RAM**: 2GB minimum, 4GB recommended
- **Disk Space**: 100MB for application and assets

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure your code follows PEP 8 style guidelines and includes tests for new features.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Authors

- MEOM Academy Development Team

## Support

For support, questions, or feedback:
- Open an issue on GitHub
- Email: support@meomacademy.com

## Acknowledgments

- MEOM Academy for project requirements and testing
- Open-source community for libraries and tools

## Roadmap

Future features planned:
- LAN multiplayer mode
- Question categories and difficulty levels
- Statistics and analytics dashboard
- Customizable themes and branding
- Mobile companion app for team controllers
- Cloud-based question banks
- Multilingual support

---

Made with ❤️ by MEOM Academy
