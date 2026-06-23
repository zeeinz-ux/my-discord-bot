import re
from datetime import datetime, timezone

class SpamEngine:
    def __init__(self):
        # 🌟 REVISI: Menggunakan \W* agar spasi/titik di antara huruf tetep ketangkep
        self.banned_patterns = [
            r"https?://(bit\.ly|t\.co|tinyurl\.com|shorturl\.at)", 
            r"s\W*l\W*o\W*t",         # Nangkep: slot, s.l.o.t, s l o t, sl0t
            r"j\W*u\W*d\W*i",         # Nangkep: judi, j.u.d.i, j u d i, jvd1
            r"d\W*e\W*p\W*o\W*s\W*i\W*t", # Nangkep: deposit
            r"g\W*a\W*c\W*o\W*r",     # Nangkep: gacor
            r"m\W*a\W*x\W*w\W*i\W*n", # Nangkep: maxwin
            r"(join now|click here|free crypto|giveaway)"
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.banned_patterns]

    def get_risk_score(self, message) -> int:
        if hasattr(message.author, 'guild_permissions') and message.author.guild_permissions.manage_messages:
            return 0
        
        score = 0 
        
        if hasattr(message, 'mention_everyone') and message.mention_everyone: 
            score += 5
        
        # 🌟 REVISI: Skor kata kunci jadi 5
        # Sekarang kalau kena satu kata kunci aja, skor langsung jadi 5 (Auto-spam)
        for pattern in self.compiled_patterns:
            if pattern.search(message.content):
                score += 5 
        
        if hasattr(message.author, 'created_at'):
            account_age = (datetime.now(timezone.utc) - message.author.created_at).days
            if account_age < 1: score += 5
            elif account_age < 3: score += 3
            elif account_age < 7: score += 2
            
        return score

    def is_spam_heuristic(self, message) -> bool:
        # threshold 5 sudah pas karena keyword sekarang bernilai 5
        return self.get_risk_score(message) >= 5

    def is_new_account(self, message) -> bool:
        if hasattr(message.author, 'created_at'):
            account_age = (datetime.now(timezone.utc) - message.author.created_at).days
            return account_age < 1
        return False
