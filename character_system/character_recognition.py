import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from character_system.character_system import CharacterSystem, Character

logger = logging.getLogger(__name__)

class CharacterRecognition:
    """人物识别服务"""
    
    def __init__(self, app=None):
        self.app = app
        self.character_system: CharacterSystem = None
        self.name_pattern = re.compile(r'[\u4e00-\u9fff]{2,5}(?:同志|先生|女士|小姐|教授|老师|同学|朋友|老板)?')
        self.quotes_pattern = re.compile(r'["""\'\'\']([^"""\']{2,30})["""\'\'\']')
        self.he_she_pattern = re.compile(r'(?:他|她|它)(?:说|问|告诉|叫|是|的|在|和|跟|对|把|让|给|向|为|从|到|被|觉得|认为|想|知道|觉得|觉得|认为|想|知道|觉得)')
        self.think_pattern = re.compile(r'觉得|认为|想|知道|记得|相信|感觉')
    
    def set_character_system(self, character_system: CharacterSystem):
        """设置人物系统"""
        self.character_system = character_system
    
    async def extract_characters_from_text(self, text: str, context: str = "") -> List[Dict[str, Any]]:
        """从文本中提取人物信息"""
        if not text:
            return []
        
        extracted = []
        seen_names = set()
        
        names = self.name_pattern.findall(text)
        for name in names:
            if name not in seen_names and len(name) >= 2:
                if not self._is_common_word(name):
                    seen_names.add(name)
                    description = self._extract_description_for_name(text, name)
                    
                    extracted.append({
                        "name": name,
                        "description": description,
                        "confidence": self._calculate_confidence(name, text, context)
                    })
        
        quotes = self.quotes_pattern.findall(text)
        for quote in quotes:
            if quote and len(quote) >= 2:
                speaker = self._identify_speaker(text, quote)
                if speaker and speaker not in seen_names:
                    seen_names.add(speaker)
                    extracted.append({
                        "name": speaker,
                        "description": f"引用: {quote[:50]}",
                        "confidence": 0.6
                    })
        
        return extracted
    
    def _is_common_word(self, name: str) -> bool:
        """检查是否为常见词（非人名）"""
        common_words = {
            "先生", "女士", "同志", "老师", "同学", "朋友", "老板",
            "大家", "我们", "他们", "她们", "它们", "公司", "学校",
            "今天", "明天", "昨天", "现在", "以后", "以前", "时候",
            "这个", "那个", "一个", "什么", "怎么", "为什么", "如何"
        }
        return name in common_words
    
    def _extract_description_for_name(self, text: str, name: str) -> str:
        """提取人物描述"""
        sentences = re.split(r'[。！？；\n]', text)
        
        for sentence in sentences:
            if name in sentence:
                cleaned = sentence.strip()
                if len(cleaned) > 5 and len(cleaned) < 100:
                    return cleaned
        
        return ""
    
    def _calculate_confidence(self, name: str, text: str, context: str) -> float:
        """计算识别置信度"""
        confidence = 0.5
        
        sentences = re.split(r'[。！？；\n]', text)
        for sentence in sentences:
            if name in sentence:
                if any(pronoun in sentence for pronoun in ["他说", "她", "他", "我问", "他问", "她问"]):
                    confidence += 0.2
                if any(action in sentence for action in ["告诉", "告诉", "说", "想", "觉得", "认为"]):
                    confidence += 0.1
                if any(marker in sentence for marker in ["的", "是", "在"]):
                    confidence += 0.1
        
        if context:
            if name in context:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _identify_speaker(self, text: str, quote: str) -> Optional[str]:
        """识别说话者"""
        quote_escaped = re.escape(quote[:30])
        patterns = [
            rf'{self.name_pattern}["""]*\s*[：:]\s*["""]*{quote_escaped}',
            rf'["""\'\'\']?\s*{quote_escaped}["""\'\']?\s*[-—]\s*([\u4e00-\u9fff]{{2,5}})',
            rf'([\u4e00-\u9fff]{{2,5}})\s*(?:说|道|写道|回答|表示|指出)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1) if match.lastindex else match.group(0).split(':')[0]
                if not self._is_common_word(name):
                    return name
        
        return None
    
    async def check_character_identity(
        self,
        name1: str,
        name2: str,
        text: str = "",
        context: str = ""
    ) -> Dict[str, Any]:
        """检查两个人名是否为同一人"""
        if not self.character_system:
            return {"is_same": False, "confidence": 0, "reason": "Character system not initialized"}
        
        char1 = self.character_system.find_by_name_or_alias(name1)
        char2 = self.character_system.find_by_name_or_alias(name2)
        
        if char1 and char2:
            return {
                "is_same": char1 == char2,
                "confidence": 1.0,
                "reason": "Both names are in the system",
                "character_id": char1 if char1 == char2 else None
            }
        
        similarity_score = self._calculate_name_similarity(name1, name2)
        
        if similarity_score > 0.8:
            return {
                "is_same": True,
                "confidence": similarity_score,
                "reason": "Names are very similar"
            }
        
        if text:
            mentions_together = self._check_names_together(name1, name2, text)
            if mentions_together:
                return {
                    "is_same": True,
                    "confidence": 0.7,
                    "reason": "Names mentioned together suggesting same person"
                }
        
        return {
            "is_same": False,
            "confidence": similarity_score,
            "reason": "Names appear to be different"
        }
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算名字相似度"""
        if not name1 or not name2:
            return 0.0
        
        set1 = set(name1)
        set2 = set(name2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        jaccard = intersection / union
        
        if name1 in name2 or name2 in name1:
            jaccard = max(jaccard, 0.9)
        
        return jaccard
    
    def _check_names_together(self, name1: str, name2: str, text: str) -> bool:
        """检查两个名字是否在一起提及"""
        pattern = rf'{re.escape(name1)}[^。！？]{{0,20}}{re.escape(name2)}'
        pattern2 = rf'{re.escape(name2)}[^。！？]{{0,20}}{re.escape(name1)}'
        
        return bool(re.search(pattern, text)) or bool(re.search(pattern2, text))
    
    async def process_and_register_characters(
        self,
        text: str,
        platform: str = None,
        source: str = None,
        context: str = ""
    ) -> List[Character]:
        """处理文本并注册发现的人物"""
        if not self.character_system:
            logger.warning("Character system not set")
            return []
        
        extracted = await self.extract_characters_from_text(text, context)
        
        registered = []
        for char_info in extracted:
            character, is_new = await self.character_system.get_or_create_character(
                name=char_info["name"],
                description=char_info.get("description", ""),
                platform=platform,
                source=source
            )
            
            if char_info.get("confidence", 0) > 0.5:
                await self._extract_character_attributes(character, text, char_info["name"])
            
            registered.append(character)
        
        return registered
    
    async def _extract_character_attributes(
        self,
        character: Character,
        text: str,
        name: str
    ):
        """提取人物属性"""
        sentences = [s.strip() for s in re.split(r'[。！？；\n]', text) if name in s]
        
        for sentence in sentences:
            if any(marker in sentence for marker in ["职业", "工作", "是", "当"]):
                job_match = re.search(r'(?:职业|工作|是|当)([^。！？,，]{2,10})(?:的|者|人|员)?', sentence)
                if job_match:
                    character.attributes["职业"] = job_match.group(1).strip()
            
            if any(marker in sentence for marker in ["住在", "位于", "在"]):
                location_patterns = [
                    r'住在([^。！？,，]{2,15})',
                    r'在([^。！？,，]{2,15})(?:住|生活|工作)',
                ]
                for pattern in location_patterns:
                    loc_match = re.search(pattern, sentence)
                    if loc_match:
                        location = loc_match.group(1).strip()
                        if len(location) >= 2:
                            character.attributes["位置"] = location
                            break
            
            if any(marker in sentence for marker in ["喜欢", "爱好", "兴趣"]):
                like_match = re.search(r'(?:喜欢|爱好)([^。！？,，]{2,20})', sentence)
                if like_match:
                    character.attributes["爱好"] = like_match.group(1).strip()
    
    async def analyze_conversation_context(
        self,
        messages: List[Dict[str, str]],
        platform: str = None
    ) -> Dict[str, Any]:
        """分析对话上下文中的所有人物"""
        if not messages:
            return {"characters": [], "relationships": [], "context": ""}
        
        full_text = "\n".join([msg.get("content", "") for msg in messages])
        
        characters = await self.process_and_register_characters(
            text=full_text,
            platform=platform,
            context=""
        )
        
        relationships = await self._extract_relationships(full_text, characters)
        
        character_ids = [c.id for c in characters]
        context = self.character_system.generate_context_for_characters(character_ids) if self.character_system else ""
        
        return {
            "characters": characters,
            "relationships": relationships,
            "context": context,
            "character_ids": character_ids
        }
    
    async def _extract_relationships(
        self,
        text: str,
        characters: List[Character]
    ) -> List[Dict[str, Any]]:
        """从文本中提取人物关系"""
        if not characters or len(characters) < 2:
            return []
        
        relationships = []
        
        relation_patterns = [
            (r'([\u4e00-\u9fff]{2,5})(?:和|跟|与)([\u4e00-\u9fff]{2,5})(?:是|成为)', '朋友'),
            (r'([\u4e00-\u9fff]{2,5})(?:和|跟|与)([\u4e00-\u9fff]{2,5})(?:结婚|夫妻)', '配偶'),
            (r'([\u4e00-\u9fff]{2,5})(?:的|是)([\u4e00-\u9fff]{2,5})(?:父母|父亲|母亲|爸爸|妈妈)', '父母'),
            (r'([\u4e00-\u9fff]{2,5})(?:是|当)([\u4e00-\u9fff]{2,5})(?:老师|导师)', '师生'),
            (r'([\u4e00-\u9fff]{2,5})(?:和|跟)([\u4e00-\u9fff]{2,5})(?:同事|同事)', '同事'),
            (r'([\u4e00-\u9fff]{2,5})(?:帮助|支持)([\u4e00-\u9fff]{2,5})', '帮助'),
            (r'([\u4e00-\u9fff]{2,5})(?:喜欢|爱)([\u4e00-\u9fff]{2,5})', '喜欢'),
            (r'([\u4e00-\u9fff]{2,5})(?:讨厌|恨)([\u4e00-\u9fff]{2,5})', '讨厌'),
        ]
        
        character_names = [c.name for c in characters]
        char_by_name = {c.name: c for c in characters}
        
        for pattern, rel_type in relation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name1 = match.group(1)
                name2 = match.group(2)
                
                char1 = char_by_name.get(name1)
                char2 = char_by_name.get(name2)
                
                if char1 and char2 and char1.id != char2.id:
                    relationships.append({
                        "source_id": char1.id,
                        "target_id": char2.id,
                        "type": rel_type,
                        "source_name": name1,
                        "target_name": name2
                    })
        
        return relationships
    
    async def suggest_merges(self, text: str = "") -> List[Dict[str, Any]]:
        """建议可能需要合并的人物"""
        if not self.character_system:
            return []
        
        suggestions = []
        
        all_chars = await self.character_system.get_all_characters()
        
        for i, char1 in enumerate(all_chars):
            for char2 in all_chars[i+1:]:
                similarity = self._calculate_name_similarity(char1.name, char2.name)
                
                if similarity > 0.6:
                    suggestions.append({
                        "character1_id": char1.id,
                        "character1_name": char1.name,
                        "character2_id": char2.id,
                        "character2_name": char2.name,
                        "similarity": similarity,
                        "reason": "名字相似度高"
                    })
                
                for alias1 in char1.aliases:
                    for alias2 in char2.aliases:
                        alias_similarity = self._calculate_name_similarity(alias1, alias2)
                        if alias_similarity > 0.7:
                            suggestions.append({
                                "character1_id": char1.id,
                                "character1_name": char1.name,
                                "character2_id": char2.id,
                                "character2_name": char2.name,
                                "similarity": alias_similarity,
                                "reason": f"别名相似: {alias1} vs {alias2}"
                            })
        
        return sorted(suggestions, key=lambda x: x["similarity"], reverse=True)
