import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class Character:
    """人物数据模型"""
    
    def __init__(
        self,
        character_id: str = None,
        name: str = None,
        aliases: List[str] = None,
        description: str = "",
        first_mentioned: datetime = None,
        last_mentioned: datetime = None,
        mentions_count: int = 0,
        platform: str = None,
        source: str = None,
        attributes: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.id = character_id or str(uuid.uuid4())
        self.name = name or "未知人物"
        self.aliases = aliases or []
        self.description = description
        self.first_mentioned = first_mentioned or datetime.now()
        self.last_mentioned = last_mentioned or datetime.now()
        self.mentions_count = mentions_count
        self.platform = platform
        self.source = source
        self.attributes = attributes or {}
        self.metadata = metadata or {}
        self.merged_ids: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases,
            "description": self.description,
            "first_mentioned": self.first_mentioned.isoformat() if self.first_mentioned else None,
            "last_mentioned": self.last_mentioned.isoformat() if self.last_mentioned else None,
            "mentions_count": self.mentions_count,
            "platform": self.platform,
            "source": self.source,
            "attributes": self.attributes,
            "metadata": self.metadata,
            "merged_ids": self.merged_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """从字典创建"""
        character = cls(
            character_id=data.get("id"),
            name=data.get("name"),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            mentions_count=data.get("mentions_count", 0),
            platform=data.get("platform"),
            source=data.get("source"),
            attributes=data.get("attributes", {}),
            metadata=data.get("metadata", {})
        )
        
        if data.get("first_mentioned"):
            if isinstance(data["first_mentioned"], str):
                character.first_mentioned = datetime.fromisoformat(data["first_mentioned"])
            else:
                character.first_mentioned = data["first_mentioned"]
        
        if data.get("last_mentioned"):
            if isinstance(data["last_mentioned"], str):
                character.last_mentioned = datetime.fromisoformat(data["last_mentioned"])
            else:
                character.last_mentioned = data["last_mentioned"]
        
        character.merged_ids = data.get("merged_ids", [])
        return character
    
    def update(self, updates: Dict[str, Any]):
        """更新人物信息"""
        if "name" in updates:
            self.name = updates["name"]
        if "aliases" in updates:
            self.aliases = updates["aliases"]
        if "description" in updates:
            self.description = updates["description"]
        if "platform" in updates:
            self.platform = updates["platform"]
        if "attributes" in updates:
            self.attributes.update(updates["attributes"])
        if "metadata" in updates:
            self.metadata.update(updates["metadata"])
        self.last_mentioned = datetime.now()
    
    def increment_mention(self):
        """增加提及次数"""
        self.mentions_count += 1
        self.last_mentioned = datetime.now()
    
    def add_alias(self, alias: str):
        """添加别名"""
        if alias and alias not in self.aliases:
            self.aliases.append(alias)
    
    def merge_from(self, other: 'Character'):
        """合并另一个人物"""
        if other.name and other.name != self.name:
            if self.name == "未知人物":
                self.name = other.name
            else:
                self.add_alias(other.name)
        
        for alias in other.aliases:
            self.add_alias(alias)
        
        if other.description and not self.description:
            self.description = other.description
        elif other.description:
            self.description += f"\n{other.description}"
        
        for key, value in other.attributes.items():
            if key not in self.attributes:
                self.attributes[key] = value
        
        self.mentions_count += other.mentions_count
        self.merged_ids.append(other.id)
    
    def get_context_summary(self) -> str:
        """获取用于上下文的摘要"""
        summary_parts = [f"{self.name}"]
        
        if self.aliases:
            summary_parts.append(f"(又称: {', '.join(self.aliases)})")
        
        if self.description:
            summary_parts.append(f"- {self.description}")
        
        return "".join(summary_parts)


class CharacterSystem:
    """人物管理系统"""
    
    def __init__(self, app=None, data_dir: str = None):
        self.app = app
        self.characters: Dict[str, Character] = {}
        self.name_index: Dict[str, str] = {}
        self.alias_index: Dict[str, str] = {}
        self.data_dir = Path(data_dir) if data_dir else Path("data/characters")
        self.relationships_file = self.data_dir / "relationships.json"
        self.relationships: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = None
    
    async def initialize(self):
        """初始化系统"""
        import asyncio
        self._lock = asyncio.Lock()
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        await self.load_characters()
        await self.load_relationships()
        
        logger.info(f"人物系统初始化完成，已加载 {len(self.characters)} 个人物")
    
    async def load_characters(self):
        """加载人物数据"""
        characters_file = self.data_dir / "characters.json"
        
        if characters_file.exists():
            try:
                with open(characters_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for char_data in data:
                        character = Character.from_dict(char_data)
                        self.characters[character.id] = character
                        self._update_indexes(character)
                logger.info(f"从 {characters_file} 加载了 {len(self.characters)} 个人物")
            except Exception as e:
                logger.error(f"加载人物数据失败: {e}")
    
    async def save_characters(self):
        """保存人物数据"""
        characters_file = self.data_dir / "characters.json"
        
        try:
            with open(characters_file, 'w', encoding='utf-8') as f:
                data = [char.to_dict() for char in self.characters.values()]
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存 {len(self.characters)} 个人物到 {characters_file}")
        except Exception as e:
            logger.error(f"保存人物数据失败: {e}")
    
    async def load_relationships(self):
        """加载关系数据"""
        if self.relationships_file.exists():
            try:
                with open(self.relationships_file, 'r', encoding='utf-8') as f:
                    self.relationships = json.load(f)
                logger.info(f"从 {self.relationships_file} 加载了关系数据")
            except Exception as e:
                logger.error(f"加载关系数据失败: {e}")
                self.relationships = {}
    
    async def save_relationships(self):
        """保存关系数据"""
        try:
            with open(self.relationships_file, 'w', encoding='utf-8') as f:
                json.dump(self.relationships, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存关系数据到 {self.relationships_file}")
        except Exception as e:
            logger.error(f"保存关系数据失败: {e}")
    
    def _update_indexes(self, character: Character):
        """更新索引"""
        name_lower = character.name.lower()
        self.name_index[name_lower] = character.id
        
        for alias in character.aliases:
            alias_lower = alias.lower()
            self.alias_index[alias_lower] = character.id
    
    def _remove_from_indexes(self, character: Character):
        """从索引中移除"""
        name_lower = character.name.lower()
        if name_lower in self.name_index:
            del self.name_index[name_lower]
        
        for alias in character.aliases:
            alias_lower = alias.lower()
            if alias_lower in self.alias_index:
                del self.alias_index[alias_lower]
    
    async def create_character(
        self,
        name: str,
        description: str = "",
        platform: str = None,
        source: str = None,
        **kwargs
    ) -> Character:
        """创建新人物"""
        async with self._lock:
            existing_id = self.find_by_name_or_alias(name)
            if existing_id:
                character = self.characters[existing_id]
                character.increment_mention()
                await self.save_characters()
                return character
            
            character = Character(
                name=name,
                description=description,
                platform=platform,
                source=source,
                **kwargs
            )
            
            self.characters[character.id] = character
            self._update_indexes(character)
            
            await self.save_characters()
            
            logger.info(f"创建新人物: {name} (ID: {character.id})")
            return character
    
    async def get_character(self, character_id: str) -> Optional[Character]:
        """获取人物"""
        return self.characters.get(character_id)
    
    async def update_character(self, character_id: str, updates: Dict[str, Any]) -> Optional[Character]:
        """更新人物信息"""
        async with self._lock:
            character = self.characters.get(character_id)
            if not character:
                return None
            
            old_name = character.name
            character.update(updates)
            
            if old_name != character.name:
                self._remove_from_indexes(character)
                self._update_indexes(character)
            
            await self.save_characters()
            
            logger.info(f"更新人物: {character_id}")
            return character
    
    async def delete_character(self, character_id: str) -> bool:
        """删除人物"""
        async with self._lock:
            if character_id not in self.characters:
                return False
            
            character = self.characters[character_id]
            self._remove_from_indexes(character)
            del self.characters[character_id]
            
            if character_id in self.relationships:
                del self.relationships[character_id]
            
            for other_id, relations in list(self.relationships.items()):
                self.relationships[other_id] = [
                    r for r in relations if r.get("target_id") != character_id
                ]
            
            await self.save_characters()
            await self.save_relationships()
            
            logger.info(f"删除人物: {character_id}")
            return True
    
    async def merge_characters(self, source_id: str, target_id: str) -> Optional[Character]:
        """合并两个人物"""
        async with self._lock:
            source = self.characters.get(source_id)
            target = self.characters.get(target_id)
            
            if not source or not target:
                return None
            
            target.merge_from(source)
            
            self._remove_from_indexes(source)
            
            for alias in source.aliases:
                target.add_alias(alias)
                self.alias_index[alias.lower()] = target_id
            
            if source.name.lower() not in self.name_index:
                self.name_index[source.name.lower()] = target_id
            
            for rel_id, relations in list(self.relationships.items()):
                for rel in relations:
                    if rel.get("target_id") == source_id:
                        rel["target_id"] = target_id
                        rel["source_id"] = rel_id
            
            if source_id in self.relationships:
                if target_id in self.relationships:
                    existing_ids = {r.get("target_id") for r in self.relationships[target_id]}
                    for rel in self.relationships[source_id]:
                        if rel.get("target_id") not in existing_ids:
                            rel["source_id"] = target_id
                            self.relationships[target_id].append(rel)
                else:
                    self.relationships[target_id] = self.relationships[source_id]
                del self.relationships[source_id]
            
            del self.characters[source_id]
            
            await self.save_characters()
            await self.save_relationships()
            
            logger.info(f"合并人物: {source_id} -> {target_id}")
            return target
    
    def find_by_name_or_alias(self, name: str) -> Optional[str]:
        """通过名称或别名查找"""
        name_lower = name.lower()
        
        if name_lower in self.name_index:
            return self.name_index[name_lower]
        
        if name_lower in self.alias_index:
            return self.alias_index[name_lower]
        
        return None
    
    async def get_or_create_character(
        self,
        name: str,
        description: str = "",
        platform: str = None,
        source: str = None,
        **kwargs
    ) -> tuple[Character, bool]:
        """获取或创建人物，返回(人物, 是否新建)"""
        existing_id = self.find_by_name_or_alias(name)
        
        if existing_id:
            character = self.characters[existing_id]
            character.increment_mention()
            await self.save_characters()
            return character, False
        
        character = await self.create_character(
            name=name,
            description=description,
            platform=platform,
            source=source,
            **kwargs
        )
        return character, True
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        description: str = "",
        bidirectional: bool = False
    ) -> bool:
        """添加人物关系"""
        if source_id not in self.characters or target_id not in self.characters:
            return False
        
        if source_id not in self.relationships:
            self.relationships[source_id] = []
        
        for rel in self.relationships[source_id]:
            if rel.get("target_id") == target_id and rel.get("type") == relation_type:
                rel["description"] = description
                rel["count"] = rel.get("count", 0) + 1
                await self.save_relationships()
                return True
        
        new_rel = {
            "source_id": source_id,
            "target_id": target_id,
            "type": relation_type,
            "description": description,
            "count": 1,
            "created_at": datetime.now().isoformat()
        }
        
        self.relationships[source_id].append(new_rel)
        
        if bidirectional:
            if target_id not in self.relationships:
                self.relationships[target_id] = []
            
            reverse_rel = {
                "source_id": target_id,
                "target_id": source_id,
                "type": relation_type,
                "description": description,
                "count": 1,
                "created_at": datetime.now().isoformat()
            }
            self.relationships[target_id].append(reverse_rel)
        
        await self.save_relationships()
        
        logger.info(f"添加关系: {source_id} --[{relation_type}]--> {target_id}")
        return True
    
    async def remove_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str = None
    ) -> bool:
        """移除人物关系"""
        if source_id not in self.relationships:
            return False
        
        original_length = len(self.relationships[source_id])
        
        if relation_type:
            self.relationships[source_id] = [
                r for r in self.relationships[source_id]
                if not (r.get("target_id") == target_id and r.get("type") == relation_type)
            ]
        else:
            self.relationships[source_id] = [
                r for r in self.relationships[source_id]
                if r.get("target_id") != target_id
            ]
        
        await self.save_relationships()
        
        return len(self.relationships[source_id]) < original_length
    
    async def get_character_relationships(self, character_id: str) -> List[Dict[str, Any]]:
        """获取人物的所有关系"""
        relations = []
        
        if character_id in self.relationships:
            relations.extend(self.relationships[character_id])
        
        for source_id, rels in self.relationships.items():
            if source_id != character_id:
                for rel in rels:
                    if rel.get("target_id") == character_id:
                        reverse_rel = rel.copy()
                        reverse_rel["source_id"] = character_id
                        reverse_rel["target_id"] = source_id
                        reverse_rel["is_reverse"] = True
                        relations.append(reverse_rel)
        
        return relations
    
    async def get_all_characters(self) -> List[Character]:
        """获取所有人物"""
        return list(self.characters.values())
    
    async def get_relationship_network(self) -> Dict[str, Any]:
        """获取关系网络数据"""
        nodes = []
        edges = []
        
        for character in self.characters.values():
            nodes.append({
                "id": character.id,
                "name": character.name,
                "aliases": character.aliases,
                "description": character.description,
                "mentions": character.mentions_count,
                "platform": character.platform
            })
        
        seen_edges = set()
        for source_id, rels in self.relationships.items():
            for rel in rels:
                target_id = rel.get("target_id")
                edge_key = tuple(sorted([source_id, target_id]))
                
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": source_id,
                        "target": target_id,
                        "type": rel.get("type"),
                        "description": rel.get("description"),
                        "count": rel.get("count", 1)
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_characters": len(nodes),
                "total_relationships": len(edges)
            }
        }
    
    async def search_characters(self, query: str) -> List[Character]:
        """搜索人物"""
        query_lower = query.lower()
        results = []
        
        for character in self.characters.values():
            if query_lower in character.name.lower():
                results.append(character)
                continue
            
            for alias in character.aliases:
                if query_lower in alias.lower():
                    results.append(character)
                    break
            
            if query_lower in character.description.lower():
                results.append(character)
        
        return results
    
    def generate_context_for_characters(self, character_ids: List[str]) -> str:
        """为指定人物生成上下文描述"""
        if not character_ids:
            return ""
        
        context_parts = ["\n\n【已知人物信息】"]
        
        for char_id in character_ids:
            character = self.characters.get(char_id)
            if character:
                context_parts.append(character.get_context_summary())
        
        return "\n".join(context_parts)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_chars = len(self.characters)
        total_relations = sum(len(rels) for rels in self.relationships.values())
        
        platforms = {}
        for char in self.characters.values():
            if char.platform:
                platforms[char.platform] = platforms.get(char.platform, 0) + 1
        
        relation_types = {}
        for rels in self.relationships.values():
            for rel in rels:
                rel_type = rel.get("type", "unknown")
                relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
        
        return {
            "total_characters": total_chars,
            "total_relationships": total_relations,
            "by_platform": platforms,
            "relation_types": relation_types,
            "top_mentioned": sorted(
                [(c.name, c.mentions_count) for c in self.characters.values()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
