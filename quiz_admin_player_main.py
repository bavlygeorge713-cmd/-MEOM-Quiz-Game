import sys
import os
import json
import random
import webview
from dataclasses import dataclass, field
import threading
import time
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    import ctypes

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

ADMIN_PASSWORD = "250595"
TIEBREAKER_TAG = "TIEBREAKER"


# =========================
# Data Models
# =========================
@dataclass
class Question:
    id: int
    question: str
    options: List[str]
    correct: int

    def to_dict(self, include_answer: bool = True) -> Dict[str, Any]:
        data = {"id": self.id, "question": self.question, "options": self.options}
        if include_answer:
            data["correct"] = self.correct
        return data


@dataclass
class GameState:
    team1_score: int = 0
    team2_score: int = 0
    team3_score: int = 0
    team4_score: int = 0

    remaining_questions: int = 0
    answered_questions: List[int] = field(default_factory=list)
    current_question_index: Optional[int] = None
    current_team: int = 1

    wheel_spun: bool = False
    game_started: bool = False
    game_finished: bool = False
    tiebreaker_active: bool = False
    tiebreaker_used: bool = False

    timed_out_questions: List[int] = field(default_factory=list)
    questions_results: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def reset(self, total_questions: int):
        self.team1_score = 0
        self.team2_score = 0
        self.team3_score = 0
        self.team4_score = 0
        self.remaining_questions = max(0, total_questions - 1)
        self.answered_questions = []
        self.current_question_index = None
        self.current_team = 1
        self.wheel_spun = False
        self.game_started = False
        self.game_finished = False
        self.tiebreaker_active = False
        self.tiebreaker_used = False
        self.timed_out_questions = []
        self.questions_results = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team1_score": self.team1_score,
            "team2_score": self.team2_score,
            "team3_score": self.team3_score,
            "team4_score": self.team4_score,
            "remaining_questions": self.remaining_questions,
            "answered_questions": list(self.answered_questions),
            "current_question_index": self.current_question_index,
            "current_team": self.current_team,
            "wheel_spun": self.wheel_spun,
            "game_started": self.game_started,
            "game_finished": self.game_finished,
            "tiebreaker_active": self.tiebreaker_active,
            "tiebreaker_used": self.tiebreaker_used,
            "timed_out_questions": list(self.timed_out_questions),
            "questions_results": dict(self.questions_results),
        }


@dataclass
class Settings:
    team1_name: str = "team1"
    team2_name: str = "team2"
    team3_name: str = " team3"
    team4_name: str = " team4"
    timer_duration: int = 30
    points_correct: int = 2
    points_wrong: int = 0
    enable_sound: bool = True
    enable_music: bool = True
    number_of_teams: int = 2

    def update(self, new_settings: Dict[str, Any]):
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team1_name": self.team1_name,
            "team2_name": self.team2_name,
            "team3_name": self.team3_name,
            "team4_name": self.team4_name,
            "timer_duration": self.timer_duration,
            "points_correct": self.points_correct,
            "points_wrong": self.points_wrong,
            "enable_sound": self.enable_sound,
            "enable_music": self.enable_music,
            "number_of_teams": self.number_of_teams,
        }

    def get_team_name(self, team_num: int) -> Optional[str]:
        if not 1 <= team_num <= self.number_of_teams:
            return None
        return getattr(self, f"team{team_num}_name", None)


# =========================
# Game Manager
# =========================
class GameManager:
    def __init__(self):
        self.questions: List[Question] = self._load_default_questions()
        self.state = GameState(remaining_questions=max(0, len(self.questions) - 1))
        self.settings = Settings()
        self.player_window: Optional[webview.Window] = None
        self.admin_window: Optional[webview.Window] = None
        self._sync_lock = threading.Lock()

    def _load_default_questions(self) -> List[Question]:
        default_data = [
            {
                "question": "What is the average blink rate per minute?",
                "options": ["5-10", "15-20", "25-30", "35-40"],
                "correct": 1,
            },
            {
                "question": "Which of the following is a type of eye movement disorder?",
                "options": ["Nystagmus", "Strabismus", "Amblyopia", "Ptosis"],
                "correct": 0,
            },
            {
                "question": "Which cranial nerve is responsible for innervating the lateral rectus muscle?",
                "options": ["CN III", "CN IV", "CN V", "CN VI"],
                "correct": 3,
            },
            {
                "question": "Which layer of the cornea is responsible for most of its refractive power?",
                "options": [
                    "Epithelium",
                    "Stroma",
                    "Endothelium",
                    "Descemet's membrane",
                ],
                "correct": 1,
            },
            {
                "question": "Which structure is responsible for the 'double hump' sign seen during indentation gonioscopy?",
                "options": [
                    "Ciliary body cyst",
                    "Plateau iris configuration",
                    "Iris bombe",
                    "Posterior synechiae",
                ],
                "correct": 1,
            },
            {
                "question": "What is the mechanism of action of netarsudil in glaucoma therapy?",
                "options": [
                    "Carbonic anhydrase inhibition",
                    "Alpha-2 adrenergic receptor agonism",
                    "Rho kinase (ROCK) inhibition",
                    "Prostaglandin analog receptor stimulation",
                ],
                "correct": 2,
            },
            {
                "question": "Which color is most visible to the human eye?",
                "options": ["Red", "Green", "Blue", "Yellow"],
                "correct": 0,
            },
            {
                "question": "Which medication is commonly used to treat CMV retinitis?",
                "options": ["Ganciclovir", "Acyclovir", "Fluconazole", "Ciprofloxacin"],
                "correct": 0,
            },
            {
                "question": "If you stare at a bright light and see spots, what's the term for this phenomenon?",
                "options": ["Phosphene", "Scotoma", "Floaters", "Photophobia"],
                "correct": 0,
            },
            {
                "question": "Which visual field defect is commonly associated with pituitary tumours?",
                "options": [
                    "Bitemporal hemianopia",
                    "Central scotoma",
                    "Homonymous hemianopia",
                    "Quadrantanopia",
                ],
                "correct": 0,
            },
            {
                "question": "What is the Watzke-Allen sign used to detect?",
                "options": [
                    "Central serous chorioretinopathy",
                    "Full-thickness macular hole",
                    "Epiretinal membrane",
                    "Retinal detachment",
                ],
                "correct": 1,
            },
            {
                "question": "Which mutation is linked to Best disease and what is its inheritance pattern?",
                "options": [
                    "ABCA4, autosomal recessive",
                    "BEST1 (VMD2), autosomal dominant",
                    "RPE65, X-linked",
                    "RS1, X-linked recessive",
                ],
                "correct": 1,
            },
            {
                "question": "Which famous artist had strabismus and may have seen the world differently?",
                "options": ["Monet", "Van Gogh", "Picasso", "Rembrandt"],
                "correct": 1,
            },
            {
                "question": "Which animal has the best vision on Earth?",
                "options": ["Human", "Eagle", "Mantis shrimp", "Owl"],
                "correct": 2,
            },
            {
                "question": "Which Disney princess had famously large, animated eyes?",
                "options": ["Cinderella", "Ariel", "Rapunzel (from Tangled)", "Belle"],
                "correct": 2,
            },
            {
                "question": "What is the UAE's national day celebrated?",
                "options": ["December 1", "December 2", "November 30", "January 1"],
                "correct": 1,
            },
            {
                "question": "What is a traditional form of Emirati hospitality?",
                "options": [
                    "Serving Turkish coffee",
                    "Offering Arabic coffee and dates",
                    "Serving mint tea only",
                    "Offering rose water and sweets",
                ],
                "correct": 1,
            },
            {
                "question": "In which year was the MEOM Academy established?",
                "options": ["2015", "2018", "2019", "2020"],
                "correct": 1,
            },
            {
                "question": "Which city hosts the MEOM conference every year?",
                "options": ["Riyadh", "Amman", "Dubai", "Muscat"],
                "correct": 2,
            },
            {
                "question": "What type of protective eyewear is recommended for athletes who wear glasses?",
                "options": [
                    "Regular eyeglasses",
                    "Polycarbonate sports goggles",
                    "Contact lenses only",
                    "Sunglasses",
                ],
                "correct": 1,
            },
            {
                "question": "Which of the following sports has the highest risk of eye trauma?",
                "options": ["Tennis", "Table tennis", "Boxing", "Swimming"],
                "correct": 2,
            },
            {
                "question": "Which eye test might help evaluate an athlete's performance in fast-paced sports like baseball or tennis?",
                "options": [
                    "Ishihara color test",
                    "Dynamic visual acuity test",
                    "Visual field perimetry",
                    "Tonometry",
                ],
                "correct": 1,
            },
            {
                "question": "\ud83c\udfc6 TIEBREAKER: Which famous Mona Lisa feature often confuses art critics due to her eyes?",
                "options": [
                    "Her eyes are closed",
                    "Her gaze seems to follow you",
                    "One eye is larger than the other",
                    "She has unusually colored eyes",
                ],
                "correct": 1,
            },
        ]
        # Ensure last is tiebreaker
        if default_data and TIEBREAKER_TAG not in default_data[-1]["question"].upper():
            default_data[-1]["question"] = (
                "\ud83c\udfc6 TIEBREAKER: " + default_data[-1]["question"]
            )
        return [Question(id=i, **q) for i, q in enumerate(default_data)]

    # -------------- Sync helpers --------------
    def sync_to_player(self):
        if not self.player_window:
            return

        def _sync():
            with self._sync_lock:
                try:
                    if hasattr(self.player_window, "evaluate_js"):
                        self.player_window.evaluate_js(
                            "(async () => { if(window.syncFromAdmin) await window.syncFromAdmin(); })()"
                        )
                except Exception as e:
                    print(f"Sync to player failed: {e}")

        threading.Timer(0.03, _sync).start()

    def sync_to_admin(self):
        if not self.admin_window:
            return

        def _sync():
            try:
                if hasattr(self.admin_window, "evaluate_js"):
                    self.admin_window.evaluate_js(
                        "(async () => { if(window.syncFromPlayer) await window.syncFromPlayer(); })()"
                    )
            except Exception:
                pass

        threading.Timer(0.05, _sync).start()

    # -------------- Core computations --------------
    def _recalculate_remaining_questions(self):
        total_regular = max(0, len(self.questions) - 1)
        answered_regular = sum(
            1 for idx in self.state.answered_questions if idx < len(self.questions) - 1
        )
        self.state.remaining_questions = max(0, total_regular - answered_regular)

    def get_next_team(self, current_team: int) -> int:
        num_teams = max(1, self.settings.number_of_teams)
        nxt = current_team + 1
        return 1 if nxt > num_teams else nxt

    def get_score_dict(self) -> Dict[str, int]:
        return {
            f"team{i}_score": getattr(self.state, f"team{i}_score", 0)
            for i in range(1, self.settings.number_of_teams + 1)
        }

    def determine_winner(self) -> Optional[str]:
        num_teams = max(0, self.settings.number_of_teams)
        scores = [
            (i, getattr(self.state, f"team{i}_score", 0))
            for i in range(1, num_teams + 1)
        ]
        if not scores:
            return None
        scores.sort(key=lambda x: x[1], reverse=True)
        if len(scores) > 1 and scores[0][1] == scores[1][1]:
            return "TIE"
        return f"TEAM{scores[0][0]}"

    def check_tiebreaker_condition(self) -> bool:
        if self.state.remaining_questions > 0:
            return False
        num_teams = self.settings.number_of_teams
        if num_teams < 2:
            return False
        scores = [
            getattr(self.state, f"team{i}_score", 0) for i in range(1, num_teams + 1)
        ]
        if not scores:
            return False
        top = max(scores)
        return sum(1 for s in scores if s == top) > 1

    # -------------- Question management --------------
    def add_question(
        self, question_text: str, options: List[str], correct: int
    ) -> Dict[str, Any]:
        if not question_text or not question_text.strip():
            return {"success": False, "error": "Question text cannot be empty"}
        if len(options) != 4:
            return {"success": False, "error": "Must have exactly 4 options"}
        if not all(opt.strip() for opt in options):
            return {"success": False, "error": "All options must be non-empty"}
        if not 0 <= correct < 4:
            return {"success": False, "error": "Invalid correct option index"}

        # Insert before tiebreaker
        new_id = len(self.questions) - 1
        self.questions.insert(
            new_id,
            Question(
                id=new_id,
                question=question_text.strip(),
                options=[o.strip() for o in options],
                correct=correct,
            ),
        )
        # Reindex
        for i, q in enumerate(self.questions):
            q.id = i

        self._recalculate_remaining_questions()
        self.sync_to_player()
        return {
            "success": True,
            "question_id": new_id,
            "total_questions": len(self.questions),
            "message": "Question added successfully!",
        }

    def edit_question(
        self, question_id: int, question_text: str, options: List[str], correct: int
    ) -> Dict[str, Any]:
        if not 0 <= question_id < len(self.questions):
            return {"success": False, "error": "Invalid question ID"}
        # Allow editing the tiebreaker question as requested
        if not question_text or not question_text.strip():
            return {"success": False, "error": "Question text cannot be empty"}
        if len(options) != 4 or not all(opt.strip() for opt in options):
            return {"success": False, "error": "Must have 4 non-empty options"}
        if not 0 <= correct < 4:
            return {"success": False, "error": "Invalid correct option index"}
        if self.state.game_started and question_id in self.state.answered_questions:
            return {
                "success": False,
                "error": "Cannot edit answered questions during game",
            }
        self.questions[question_id] = Question(
            id=question_id,
            question=question_text.strip(),
            options=[o.strip() for o in options],
            correct=correct,
        )
        self.sync_to_player()
        return {"success": True, "message": "Question updated successfully!"}

    def delete_question(self, question_id: int) -> Dict[str, Any]:
        if not 0 <= question_id < len(self.questions):
            return {"success": False, "error": "Invalid question ID"}
        # Keep protection on deleting the tiebreaker question
        if question_id == len(self.questions) - 1:
            return {"success": False, "error": "Cannot delete tiebreaker question"}
        if self.state.game_started and question_id not in self.state.answered_questions:
            return {
                "success": False,
                "error": "Cannot delete unanswered questions during game",
            }

        self.questions.pop(question_id)
        # Reindex
        for i, q in enumerate(self.questions):
            q.id = i
        # Reindex answered/timed out
        self.state.answered_questions = [
            idx if idx < question_id else idx - 1
            for idx in self.state.answered_questions
            if idx != question_id
        ]
        self.state.timed_out_questions = [
            idx if idx < question_id else idx - 1
            for idx in self.state.timed_out_questions
            if idx != question_id
        ]
        if self.state.questions_results:
            new_map = {}
            for idx, data in self.state.questions_results.items():
                if idx == question_id:
                    continue
                new_idx = idx if idx < question_id else idx - 1
                new_map[new_idx] = data
            self.state.questions_results = new_map

        self._recalculate_remaining_questions()
        self.sync_to_player()
        return {
            "success": True,
            "message": "Question deleted successfully!",
            "total_questions": len(self.questions),
        }


game_manager = GameManager()


# =========================
# APIs
# =========================
class AdminAPI:
    def verify_password(self, password: str) -> Dict[str, Any]:
        return {
            "success": password == ADMIN_PASSWORD,
            "message": "OK" if password == ADMIN_PASSWORD else "Invalid",
        }

    def get_all_questions(self) -> Dict[str, Any]:
        return {
            "success": True,
            "questions": [q.to_dict() for q in game_manager.questions],
        }

    def add_question(
        self, question_text: str, options: List[str], correct_index: int
    ) -> Dict[str, Any]:
        return game_manager.add_question(question_text, options, correct_index)

    def edit_question(
        self,
        question_id: int,
        question_text: str,
        options: List[str],
        correct_index: int,
    ) -> Dict[str, Any]:
        return game_manager.edit_question(
            question_id, question_text, options, correct_index
        )

    def delete_question(self, question_id: int) -> Dict[str, Any]:
        return game_manager.delete_question(question_id)

    def get_settings(self) -> Dict[str, Any]:
        return {"success": True, "settings": game_manager.settings.to_dict()}

    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        new_num = settings.get("number_of_teams", game_manager.settings.number_of_teams)
        if not 2 <= int(new_num) <= 4:
            return {
                "success": False,
                "error": "Number of teams must be between 2 and 4",
            }
        old_num = game_manager.settings.number_of_teams
        game_manager.settings.update(settings)
        # Clamp current_team
        if game_manager.state.current_team > game_manager.settings.number_of_teams:
            game_manager.state.current_team = 1
        # Zero scores for removed teams
        for i in range(game_manager.settings.number_of_teams + 1, 5):
            setattr(game_manager.state, f"team{i}_score", 0)
        # Recalc remaining if not started
        if not game_manager.state.game_started:
            game_manager._recalculate_remaining_questions()
        game_manager.sync_to_player()
        return {
            "success": True,
            "message": "Settings updated!",
            "settings": game_manager.settings.to_dict(),
        }

    def get_game_state(self) -> Dict[str, Any]:
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def force_spin_wheel(self, team_number: int) -> Dict[str, Any]:
        if game_manager.state.wheel_spun:
            return {"success": False, "error": "Wheel already spun"}
        if not 1 <= team_number <= game_manager.settings.number_of_teams:
            return {
                "success": False,
                "error": f"Invalid team (1-{game_manager.settings.number_of_teams})",
            }
        game_manager.state.current_team = team_number
        game_manager.state.wheel_spun = True
        game_manager.sync_to_player()
        return {
            "success": True,
            "starting_team": team_number,
            "team_name": game_manager.settings.get_team_name(team_number),
        }

    def force_start_game(self) -> Dict[str, Any]:
        if not game_manager.state.wheel_spun:
            return {"success": False, "error": "Wheel must be spun first"}
        game_manager.state.game_started = True
        game_manager.sync_to_player()
        return {"success": True, "message": "Game started"}

    def manual_score_set(self, team: int, score: int) -> Dict[str, Any]:
        if not 1 <= team <= game_manager.settings.number_of_teams:
            return {"success": False, "error": "Invalid team"}
        setattr(game_manager.state, f"team{team}_score", max(0, int(score)))
        game_manager.sync_to_player()
        return {"success": True, "message": f"Team {team} score set to {score}"}

    def reset_game(self) -> Dict[str, Any]:
        game_manager.state.reset(len(game_manager.questions))
        game_manager.sync_to_player()
        return {"success": True, "message": "Game reset"}

    def export_questions(self) -> Dict[str, Any]:
        return {
            "success": True,
            "data": json.dumps([q.to_dict() for q in game_manager.questions], indent=2),
        }

    def import_questions(self, json_data: str) -> Dict[str, Any]:
        try:
            imported = json.loads(json_data)
            if not isinstance(imported, list) or not imported:
                return {"success": False, "error": "Invalid format"}
            for q in imported:
                if not all(k in q for k in ["question", "options", "correct"]):
                    return {"success": False, "error": "Missing fields"}
                if len(q.get("options", [])) != 4:
                    return {
                        "success": False,
                        "error": "Each question must have 4 options",
                    }
                if not 0 <= q.get("correct", -1) < 4:
                    return {"success": False, "error": "Invalid correct answer index"}
            # Ensure last is tiebreaker
            if (
                imported
                and TIEBREAKER_TAG not in imported[-1].get("question", "").upper()
            ):
                imported[-1]["question"] = "\ud83c\udfc6 TIEBREAKER: " + imported[
                    -1
                ].get("question", "")
            game_manager.questions = [
                Question(id=i, **q) for i, q in enumerate(imported)
            ]
            if not game_manager.state.game_started:
                game_manager._recalculate_remaining_questions()
            game_manager.sync_to_player()
            return {
                "success": True,
                "message": f"Imported {len(game_manager.questions)} questions",
                "total_questions": len(game_manager.questions),
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON"}

    def open_player_window(self) -> Dict[str, Any]:
        if game_manager.player_window:
            try:
                game_manager.player_window.destroy()
            except Exception:
                pass
            finally:
                game_manager.player_window = None
        threading.Timer(0.1, create_player_window).start()
        return {"success": True, "message": "Opening player window..."}

    def exit_application(self) -> Dict[str, Any]:
        try:
            if game_manager.admin_window:
                game_manager.admin_window.destroy()
            if game_manager.player_window:
                game_manager.player_window.destroy()
        except Exception:
            pass
        finally:
            try:
                webview.destroy_window()
            except Exception:
                pass
        return {"success": True}


class PlayerAPI:
    def open_admin_panel(self, password: str) -> Dict[str, Any]:
        if password != ADMIN_PASSWORD:
            return {"success": False, "error": "Invalid password"}
        if not game_manager.admin_window:
            threading.Timer(0.1, create_admin_window_from_player).start()
        return {"success": True, "message": "Admin panel opening..."}

    def close_player_window(self) -> Dict[str, Any]:
        try:
            if game_manager.player_window:
                game_manager.player_window.destroy()
                game_manager.player_window = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def exit_application(self) -> Dict[str, Any]:
        try:
            if game_manager.admin_window:
                game_manager.admin_window.destroy()
            if game_manager.player_window:
                game_manager.player_window.destroy()
        except Exception:
            pass
        finally:
            try:
                webview.destroy_window()
            except Exception:
                pass
        return {"success": True}

    def reset_game(self) -> Dict[str, Any]:
        game_manager.state.reset(len(game_manager.questions))
        game_manager.sync_to_admin()
        game_manager.sync_to_player()
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def spin_wheel(self) -> Dict[str, Any]:
        # Allow respin any time before game starts
        if game_manager.state.game_started:
            return {"success": False, "error": "Cannot spin wheel after game started"}
        num_teams = game_manager.settings.number_of_teams
        if num_teams < 2:
            return {"success": False, "error": "Invalid team count"}
        starting_team = random.randint(1, num_teams)
        game_manager.state.current_team = starting_team
        game_manager.state.wheel_spun = True
        game_manager.sync_to_admin()
        return {
            "success": True,
            "starting_team": starting_team,
            "team_name": game_manager.settings.get_team_name(starting_team),
            "number_of_teams": num_teams,
        }

    def start_game(self) -> Dict[str, Any]:
        if not game_manager.state.wheel_spun:
            return {"success": False, "error": "Spin wheel first"}
        game_manager.state.game_started = True
        game_manager.sync_to_admin()
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def get_question(self, question_index: int) -> Dict[str, Any]:
        if not game_manager.state.game_started:
            return {"success": False, "error": "Game not started"}
        if not 0 <= question_index < len(game_manager.questions):
            return {"success": False, "error": "Invalid question"}
        if question_index in game_manager.state.answered_questions:
            return {"success": False, "error": "Already answered"}
        is_tiebreaker = question_index == len(game_manager.questions) - 1
        if game_manager.state.tiebreaker_active and not is_tiebreaker:
            return {"success": False, "error": "Tiebreaker is active"}
        if not game_manager.state.tiebreaker_active and is_tiebreaker:
            return {"success": False, "error": "Tiebreaker not yet available"}
        game_manager.state.current_question_index = question_index
        return {
            "success": True,
            "question": game_manager.questions[question_index].to_dict(
                include_answer=False
            ),
            "current_team": game_manager.state.current_team,
            "is_tiebreaker": is_tiebreaker,
        }

    def check_answer(self, question_index: int, selected_option: int) -> Dict[str, Any]:
        try:
            if not 0 <= question_index < len(game_manager.questions):
                return {"success": False, "error": "Invalid question"}
            if question_index in game_manager.state.answered_questions:
                return {"success": False, "error": "Question already answered"}
            question = game_manager.questions[question_index]
            correct = selected_option == question.correct
            is_tiebreaker = question_index == len(game_manager.questions) - 1
            current_team = game_manager.state.current_team
            if is_tiebreaker and not game_manager.state.tiebreaker_active:
                return {"success": False, "error": "Tiebreaker not yet available"}
            # Scoring
            if not is_tiebreaker:
                curr = getattr(game_manager.state, f"team{current_team}_score", 0)
                delta = (
                    game_manager.settings.points_correct
                    if correct
                    else game_manager.settings.points_wrong
                )
                setattr(
                    game_manager.state,
                    f"team{current_team}_score",
                    max(0, curr + delta),
                )
            # Persist per-question result
            game_manager.state.questions_results[question_index] = {
                "team": current_team,
                "correct": bool(correct),
            }
            # Lock question
            game_manager.state.answered_questions.append(question_index)
            if not is_tiebreaker:
                game_manager._recalculate_remaining_questions()
            if question_index in game_manager.state.timed_out_questions:
                game_manager.state.timed_out_questions.remove(question_index)
            # Flow
            game_ended = False
            winner = None
            if is_tiebreaker:
                if correct:
                    game_manager.state.game_finished = True
                    game_manager.state.tiebreaker_active = False
                    game_manager.state.tiebreaker_used = True
                    game_ended = True
                    winner = f"TEAM{current_team}"
                else:
                    game_manager.state.current_team = game_manager.get_next_team(
                        current_team
                    )
            else:
                game_manager.state.current_team = game_manager.get_next_team(
                    current_team
                )
                if game_manager.state.remaining_questions == 0:
                    if game_manager.check_tiebreaker_condition():
                        game_manager.state.tiebreaker_active = True
                        game_manager.state.tiebreaker_used = True
                    else:
                        game_manager.state.game_finished = True
                        game_ended = True
                        winner = game_manager.determine_winner()
            game_manager.sync_to_admin()
            return {
                "success": True,
                "is_correct": correct,
                "correct": correct,
                "correct_answer": question.correct,
                "game_state": game_manager.state.to_dict(),
                "current_team": game_manager.state.current_team,
                "game_ended": game_ended,
                "winner": winner,
                **game_manager.get_score_dict(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_timeout(self, question_index: int) -> Dict[str, Any]:
        try:
            if not 0 <= question_index < len(game_manager.questions):
                return {"success": False, "error": "Invalid question"}
            is_tiebreaker = question_index == len(game_manager.questions) - 1
            current_team = game_manager.state.current_team
            if is_tiebreaker and not game_manager.state.tiebreaker_active:
                return {"success": False, "error": "Tiebreaker not yet available"}
            if question_index not in game_manager.state.answered_questions:
                game_manager.state.answered_questions.append(question_index)
            if question_index not in game_manager.state.timed_out_questions:
                game_manager.state.timed_out_questions.append(question_index)
            if not is_tiebreaker:
                game_manager._recalculate_remaining_questions()
            game_manager.state.current_team = game_manager.get_next_team(current_team)
            game_ended = False
            winner = None
            if not is_tiebreaker and game_manager.state.remaining_questions == 0:
                if game_manager.check_tiebreaker_condition():
                    game_manager.state.tiebreaker_active = True
                    game_manager.state.tiebreaker_used = True
                else:
                    game_manager.state.game_finished = True
                    game_ended = True
                    winner = game_manager.determine_winner()
            game_manager.sync_to_admin()
            return {
                "success": True,
                "game_state": game_manager.state.to_dict(),
                "game_ended": game_ended,
                "winner": winner,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def switch_team(self) -> Dict[str, Any]:
        game_manager.state.current_team = game_manager.get_next_team(
            game_manager.state.current_team
        )
        game_manager.sync_to_admin()
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def restart_game(self) -> Dict[str, Any]:
        game_manager.state.reset(len(game_manager.questions))
        game_manager.sync_to_admin()
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def get_game_state(self) -> Dict[str, Any]:
        return {"success": True, "game_state": game_manager.state.to_dict()}

    def get_settings(self) -> Dict[str, Any]:
        return {"success": True, "settings": game_manager.settings.to_dict()}


# =========================
# Window creation
# =========================


def get_web_path() -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base_path / "web"
    return Path(__file__).parent.absolute() / "web"


def get_screen_size() -> Tuple[int, int]:
    if sys.platform == "win32":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    return 1920, 1080


def create_admin_window_from_player():
    html_file = str(get_web_path() / "admin.html")
    width, height = get_screen_size()
    w = int(width * 0.8)
    h = int(height * 0.85)
    w = max(1024, min(w, 1600))
    h = max(768, min(h, 1000))

    game_manager.admin_window = webview.create_window(
        "Admin Panel",
        html_file,
        js_api=AdminAPI(),
        width=w,
        height=h,
        resizable=True,
        min_size=(1024, 768),
    )

    def cleanup():
        game_manager.admin_window = None

    game_manager.admin_window.events.closed += cleanup


def create_player_window():
    html_file = str(get_web_path() / "player.html")
    game_manager.player_window = webview.create_window(
        "MEOM Quiz",
        html_file,
        js_api=PlayerAPI(),
        fullscreen=True,  # Cover entire monitor
        resizable=False,  # Not resizable
        frameless=False,  # Use system frame to avoid draggable surface
        easy_drag=False,  # Ensure no drag helpers (if backend supports)
    )

    def cleanup():
        game_manager.player_window = None

    game_manager.player_window.events.closed += cleanup


# =========================
# Main
# =========================


def start():
    print("=" * 60)
    print("MEOM Quiz Game - Desktop Application")
    print(f"Questions: {len(game_manager.questions)}")
    print("=" * 60)
    create_player_window()
    webview.start(debug=False)


if __name__ == "__main__":
    start()
