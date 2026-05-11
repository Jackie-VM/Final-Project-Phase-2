import json
from pathlib import Path
from openai import OpenAI


class SalonContextStore:
    def __init__(
        self,
        users_path: str,
        appointments_path: str,
        inventory_path: str,
        feedback_path: str
    ):
        self.users_path = Path(users_path)
        self.appointments_path = Path(appointments_path)
        self.inventory_path = Path(inventory_path)
        self.feedback_path = Path(feedback_path)

    def _load_json(self, filepath: Path) -> list:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def get_salon_context_as_string(
        self,
        current_user: dict,
        role: str,
        service_prices: dict,
        reward_options: list,
        employee_names: list
    ) -> str:
        """
        Reads salon data and returns a formatted JSON string for the AI.
        This is the business context that gets injected into the hidden prompt.
        """

        users = self._load_json(self.users_path)
        appointments = self._load_json(self.appointments_path)
        inventory = self._load_json(self.inventory_path)
        feedback = self._load_json(self.feedback_path)

        user_email = current_user.get("email", "")
        user_name = current_user.get("full_name", "")

        # Customers should only get their own appointment and feedback context.
        if role == "Customer":
            visible_appointments = []

            for appt in appointments:
                if appt.get("client_email") == user_email:
                    visible_appointments.append(appt)

            visible_feedback = []

            for item in feedback:
                if item.get("customer_email") == user_email:
                    visible_feedback.append(item)

            context = {
                "current_user": {
                    "full_name": user_name,
                    "email": user_email,
                    "role": role,
                    "reward_points": current_user.get("reward_points", 0),
                    "reward_history": current_user.get("reward_history", [])
                },
                "available_services": service_prices,
                "reward_options": reward_options,
                "employee_names": employee_names,
                "customer_appointments": visible_appointments,
                "customer_feedback": visible_feedback
            }

        # Employees can see assigned appointments, inventory, and feedback context.
        elif role == "Employee":
            visible_appointments = []

            for appt in appointments:
                if appt.get("employee") == user_name:
                    visible_appointments.append(appt)

            context = {
                "current_user": {
                    "full_name": user_name,
                    "email": user_email,
                    "role": role
                },
                "available_services": service_prices,
                "reward_options": reward_options,
                "employee_names": employee_names,
                "employee_appointments": visible_appointments,
                "inventory": inventory,
                "feedback": feedback
            }

        else:
            context = {
                "current_user": {
                    "full_name": user_name,
                    "email": user_email,
                    "role": role
                },
                "available_services": service_prices,
                "reward_options": reward_options,
                "employee_names": employee_names
            }

        return json.dumps(context, indent=2)


class ChatLoggerStore:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

    def load_logs(self) -> list:
        """
        Reads existing chat logs or returns an empty list.
        """
        if self.filepath.exists():
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_logs(self, logs: list) -> None:
        """
        Saves the entire list of chat logs back to the file.
        """
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)

    def load_logs_for_user(self, user_email: str) -> list:
        """
        Restores only the visible user/assistant pairs for the current user.
        """
        all_logs = self.load_logs()
        user_logs = []

        for log in all_logs:
            if log.get("user_email") == user_email:
                user_logs.append(log)

        return user_logs

    def append_log(self, user_email: str, user_message: str, assistant_message: str) -> None:
        """
        Saves only the real user/assistant interaction.
        The hidden AI prompt is not saved.
        """
        logs = self.load_logs()

        logs.append({
            "user_email": user_email,
            "user_message": user_message,
            "assistant_message": assistant_message
        })

        self.save_logs(logs)

    def clear_logs_for_user(self, user_email: str) -> None:
        """
        Clears saved chat history for only the current user.
        """
        logs = self.load_logs()
        kept_logs = []

        for log in logs:
            if log.get("user_email") != user_email:
                kept_logs.append(log)

        self.save_logs(kept_logs)

