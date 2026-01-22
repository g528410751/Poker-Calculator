"""
DeepSeek API 集成模块 - 提供德州扑克决策建议
"""
import os
from typing import List, Dict, Optional, Generator
from poker_calculator import Card

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class DeepSeekAdvisor:
    """DeepSeek AI 决策顾问"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化 DeepSeek API 客户端"""
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        
        if not self.api_key:
            raise ValueError("未提供 DeepSeek API Key")
        
        if OpenAI is None:
            raise ImportError("请安装 openai 库: pip install openai")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
    
    def get_decision_stream(self, 
                           hole_cards: List[Card],
                           community_cards: List[Card],
                           pot_size: float,
                           current_bet: float,
                           your_stack: float,
                           position: str,
                           num_opponents: int,
                           win_probability: float,
                           current_hand: str,
                           game_stage: str,
                           outs_info: str = "") -> Generator[str, None, None]:
        """获取 AI 决策建议 (流式输出)"""
        prompt = self._build_prompt(
            hole_cards, community_cards, pot_size, current_bet, 
            your_stack, position, num_opponents, win_probability,
            current_hand, game_stage, outs_info
        )
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": """你是专业德州扑克教练，结合GTO策略和实战经验给出建议。

输出格式：
## 决策：【弃牌/跟注/加注X/全下】

**分析：**
1. 手牌评估：XX的价值和潜力
2. 赢率分析：赢率XX% vs 底池赔率XX%，是否有利可图
3. 位置因素：当前位置的优势/劣势
4. 对手范围：对手可能的牌型范围
5. 风险提示：需要注意的点

请用中文，简洁但全面。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=400,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"❌ 错误: {str(e)}"
    
    def _build_prompt(self, hole_cards, community_cards, pot_size, current_bet,
                     your_stack, position, num_opponents, win_probability,
                     current_hand, game_stage, outs_info="") -> str:
        """构建提示词"""
        hole_str = ' '.join([str(card) for card in hole_cards])
        community_str = ' '.join([str(card) for card in community_cards]) if community_cards else '无'
        
        # 计算底池赔率（需要的最低赢率）
        if current_bet > 0 and (pot_size + current_bet) > 0:
            pot_odds = current_bet / (pot_size + current_bet)
            pot_odds_str = f"{pot_odds:.1%}"
        else:
            pot_odds_str = "0%（不需跟注）"
        
        # 计算有效筹码比
        spr = your_stack / pot_size if pot_size > 0 else 999
        
        prompt = f"""当前牌局：
• 阶段: {game_stage}
• 手牌: {hole_str}
• 公共牌: {community_str}
• 当前牌型: {current_hand}

数据分析：
• 赢率: {win_probability:.1%} (对抗{num_opponents}人)
• 底池赔率: {pot_odds_str}
• 底池: {pot_size:.0f} | 跟注: {current_bet:.0f} | 筹码: {your_stack:.0f}
• SPR: {spr:.1f}
• 位置: {position}"""
        
        if outs_info:
            prompt += f"\n• Outs: {outs_info}"
        
        prompt += "\n\n请给出决策建议。"
        return prompt

    def parse_action_from_text(self, text: str) -> Dict:
        """从AI响应文本第一行解析决策"""
        first_line = text.split('\n')[0] if text else ""
        
        if '【弃牌】' in first_line:
            return {'action': '弃牌', 'color': '🔴'}
        elif '【全下】' in first_line:
            return {'action': '全下', 'color': '🟣'}
        elif '【加注' in first_line:
            return {'action': '加注', 'color': '🟢'}
        elif '【跟注】' in first_line:
            return {'action': '跟注', 'color': '🟡'}
        return {'action': '分析中', 'color': '⚪'}
    
    def _get_basic_advice(self, win_probability: float, pot_size: float, current_bet: float) -> str:
        """基于简单规则的后备建议"""
        pot_odds = current_bet / (pot_size + current_bet) if (pot_size + current_bet) > 0 else 0
        
        if win_probability > pot_odds + 0.15:
            return f"【加注】赢率{win_probability:.1%} >> 底池赔率{pot_odds:.1%}"
        elif win_probability > pot_odds:
            return f"【跟注】赢率{win_probability:.1%} > 底池赔率{pot_odds:.1%}"
        else:
            return f"【弃牌】赢率{win_probability:.1%} < 底池赔率{pot_odds:.1%}"
    
    def analyze_opponent_range(self, 
                               opponent_action: str,
                               position: str,
                               game_stage: str,
                               community_cards: List[Card]) -> str:
        """
        分析对手可能的手牌范围
        
        参数：
            opponent_action: 对手的行动（加注/跟注/弃牌等）
            position: 对手位置
            game_stage: 游戏阶段
            community_cards: 公共牌
        """
        community_str = ', '.join([str(card) for card in community_cards]) if community_cards else '无'
        
        prompt = f"""
请分析对手的可能手牌范围：

- 对手行动: {opponent_action}
- 对手位置: {position}
- 游戏阶段: {game_stage}
- 公共牌: {community_str}

请给出：
1. 对手可能的手牌范围
2. 强手牌的可能性
3. 诈唬的可能性
4. 建议的应对策略
"""
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的德州扑克分析师，擅长根据对手行为推断手牌范围。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"分析失败: {str(e)}"
