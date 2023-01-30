from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase

from chat.models import Room, Message, Streak

class ChatTestCase(TestCase):
    def setUp(self):
        self.date = timezone.now()
        aaa = User.objects.create(username="AAA", password="rrrrrrrr")
        bbb = User.objects.create(username="BBB", password="rrrrrrrr")
        room = Room.objects.create(title="Test Room", type=Room.Type.PEER2PEER)
        room.participants.add(aaa)
        room.participants.add(bbb)
    
    def create_chat(self, date: timezone):
        room = Room.objects.get(title="Test Room")
        aaa = User.objects.get(username="AAA")
        bbb = User.objects.get(username="BBB")
        m1 = Message.objects.create(
            author=aaa, 
            room=room, 
            type=Message.Type.TEXT, 
            content="RRR nabersin RRR", 
        )
        m2 = Message.objects.create(
            author=bbb, 
            room=room, 
            type=Message.Type.TEXT, 
            content="RRR iyiyim RRR", 
        )
        m3 = Message.objects.create(
            author=aaa, 
            room=room, 
            type=Message.Type.TEXT, 
            content="RRR beni sorsana RRR", 
        )
        m4 = Message.objects.create(
            author=bbb, 
            room=room, 
            type=Message.Type.TEXT, 
            content="RRR yooo RRR", 
        )
        m1.timestamp = date
        m2.timestamp = date
        m3.timestamp = date
        m4.timestamp = date
        m1.save()
        m2.save()
        m3.save()
        m4.save()
        print(f"Messages created for day: {date}")
    
    def get_day(self):
        return self.date
    
    def move_a_day(self):
        self.date = self.date + timedelta(days=1)
    
    # def test_messaging_is_possible(self):
    #   room = Room.objects.get(title="Test Room")
    #   aaa = User.objects.get(username="AAA")
    #   message = Message.objects.get(author=aaa, room=room, content="RRR nabersin RRR")
    #   self.assertEqual(message.content, "RRR nabersin RRR")
    
    def test_streak_working(self):
        room = Room.objects.get(title="Test Room")
        streak = Streak.objects.get(room=room)
        for i in range(5):
            print(f"=========== Day {i} ==============")
            self.create_chat(self.get_day())
            self.move_a_day()
            print(f"xp: {streak.collected_xp}")
            streak.update_streak(self.get_day())
        self.move_a_day()
        self.date = self.date + timedelta(seconds=300)
        for i in range(5):
            print(f"=========== Day {i} ==============")
            self.create_chat(self.get_day())
            self.move_a_day()
            print(f"xp: {streak.collected_xp}")
            streak.update_streak(self.get_day())
