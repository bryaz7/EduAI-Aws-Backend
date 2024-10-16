from typing import Optional

from db.models.base_table import BaseTable
from db.models.user_person_ai import UserPersonAI
from db.extension import db
from utils.exceptions import ConversationNotFoundError, MediaNotFoundError, ValidationError
from services.aws_service import delete_item_on_message_history


class HistoryMessage(BaseTable):
    __tablename__ = "history_message"

    id = db.Column(db.Integer, primary_key=True)
    user_person_ai_id = db.Column(db.Integer, db.ForeignKey('user_person_ai.id', ondelete='CASCADE'))
    message_uri = db.Column(db.String(255))
    note = db.Column(db.JSON)
    media = db.Column(db.JSON)
    file = db.Column(db.JSON)

    history_message_reports = db.relationship("HistoryMessageReport", cascade="all, delete")

    @staticmethod
    def get_id_by_user_person_ai_id(user_person_ai_id):
        history_message = db.session.query(HistoryMessage) \
            .filter(HistoryMessage.user_person_ai_id == user_person_ai_id) \
            .first()
        if history_message:
            return history_message.id
        else:
            return None

    @staticmethod
    def get_by_user_person_ai_id(user_person_ai_id):
        return db.session.query(HistoryMessage) \
            .filter(HistoryMessage.user_person_ai_id == user_person_ai_id) \
            .first()

    @staticmethod
    def get_media_by_id(message_id):
        result = db.session.query(HistoryMessage.media) \
            .filter(HistoryMessage.id == message_id) \
            .first()
        if result:
            return {
                'message_id': message_id,
                'media': result.media
            }

    @staticmethod
    def get_notes_by_id(message_id):
        result = db.session.query(HistoryMessage.note) \
            .filter(HistoryMessage.id == message_id) \
            .first()
        if result:
            return {
                'message_id': message_id,
                'notes': result.note
            }

    @staticmethod
    def get_files_by_id(message_id):
        result = db.session.query(HistoryMessage.file) \
            .filter(HistoryMessage.id == message_id) \
            .first()
        if result:
            return {
                'message_id': message_id,
                'files': result.file
            }

    def append_file(self, file_url, timestamp):
        file_metadata_obj = {
            'created_at': timestamp,
            'url': file_url
        }
        self.file = self.file + [file_metadata_obj]
        db.session.commit()

    def append_media(self, media_url, timestamp, image_size):
        media_metadata_obj = {
            'created_at': timestamp,
            'url': media_url,
            'size': image_size
        }
        self.media = self.media + [media_metadata_obj]
        db.session.commit()

    def append_note(self, note, timestamp):
        if self.check_note_is_saved(timestamp):
            raise ValidationError("Note is already saved")
        self.note = self.note + [{
            "timestamp": timestamp,
            "note": note
        }]
        db.session.commit()

    def delete_media(self, media_url):
        # File all media with the specified url
        media_without_url = [i for i in self.media if i.get('url') != media_url]
        media_with_url = [i for i in self.media if i.get('url') == media_url]

        if len(media_with_url) == 1:
            # Found 1 with specified URL, deleting on message history using the attached timestamp
            timestamp = media_with_url[0]["created_at"]

            if delete_item_on_message_history(self.id, timestamp):
                self.media = media_without_url
                db.session.commit()
            else:
                raise MediaNotFoundError("Cannot find media on NoSQL DBMS")
        else:
            raise MediaNotFoundError("Cannot find media on RDBMS")

    def get_size(self):
        return sum([media.get('size', 0) for media in self.media])

    @staticmethod
    def get_message_history_id_by_user_or_parent(person_ai_id, id, role, exc=True):
        # Check if room exists
        user_person_ai_id: Optional[UserPersonAI] = UserPersonAI.get_user_person_ai_by_chatter(id, person_ai_id, role)

        if user_person_ai_id:
            history_message: HistoryMessage = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)
            if not history_message:
                if exc:
                    raise ConversationNotFoundError("Error while entering the chat (history message not found)")
                else:
                    return None, None
            message_id = history_message.id
        else:
            if exc:
                raise ConversationNotFoundError("Error while entering the chat (user-agent pair not found)")
            else:
                return None, None
        return history_message, message_id

    def check_note_is_saved(self, timestamp):
        saved_timestamps = [note["timestamp"] for note in self.note]
        return timestamp in saved_timestamps
