"""
德州扑克概率计算器核心模块
"""
import random
from itertools import combinations
from collections import Counter
from typing import List, Tuple, Dict

class Card:
    """扑克牌类"""
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    RANK_VALUES = {rank: i for i, rank in enumerate(RANKS)}
    
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.value = self.RANK_VALUES[rank]
    
    def __repr__(self):
        return f"{self.rank}{self.suit}"
    
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
    
    def __hash__(self):
        return hash((self.rank, self.suit))


class Deck:
    """牌堆类"""
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS]
    
    def remove_cards(self, cards: List[Card]):
        """从牌堆中移除指定的牌"""
        for card in cards:
            self.cards = [c for c in self.cards if not (c.rank == card.rank and c.suit == card.suit)]
    
    def draw(self, n: int) -> List[Card]:
        """随机抽取n张牌"""
        return random.sample(self.cards, n)


class HandEvaluator:
    """手牌评估器"""
    
    @staticmethod
    def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int]]:
        """
        评估手牌强度
        返回：(手牌类型, 关键牌值列表)
        手牌类型：9-皇家同花顺, 8-同花顺, 7-四条, 6-葫芦, 5-同花, 4-顺子, 3-三条, 2-两对, 1-一对, 0-高牌
        """
        if len(cards) < 5:
            return (0, [])
        
        # 获取所有5张牌的组合
        best_hand = (0, [])
        for combo in combinations(cards, 5):
            hand_type, key_cards = HandEvaluator._evaluate_five_cards(list(combo))
            if hand_type > best_hand[0] or (hand_type == best_hand[0] and key_cards > best_hand[1]):
                best_hand = (hand_type, key_cards)
        
        return best_hand
    
    @staticmethod
    def _evaluate_five_cards(cards: List[Card]) -> Tuple[int, List[int]]:
        """评估5张牌"""
        ranks = [c.value for c in cards]
        suits = [c.suit for c in cards]
        rank_counts = Counter(ranks)
        
        is_flush = len(set(suits)) == 1
        sorted_ranks = sorted(ranks, reverse=True)
        is_straight = HandEvaluator._is_straight(sorted_ranks)
        
        # 特殊处理A-2-3-4-5的顺子
        if sorted_ranks == [12, 3, 2, 1, 0]:  # A-5-4-3-2
            is_straight = True
            sorted_ranks = [3, 2, 1, 0, -1]  # A在这种情况下值最小
        
        # 皇家同花顺
        if is_flush and is_straight and sorted_ranks == [12, 11, 10, 9, 8]:
            return (9, sorted_ranks)
        
        # 同花顺
        if is_flush and is_straight:
            return (8, sorted_ranks)
        
        # 四条
        if 4 in rank_counts.values():
            four_rank = [r for r, count in rank_counts.items() if count == 4][0]
            kicker = [r for r in ranks if r != four_rank][0]
            return (7, [four_rank, kicker])
        
        # 葫芦
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            three_rank = [r for r, count in rank_counts.items() if count == 3][0]
            pair_rank = [r for r, count in rank_counts.items() if count == 2][0]
            return (6, [three_rank, pair_rank])
        
        # 同花
        if is_flush:
            return (5, sorted_ranks)
        
        # 顺子
        if is_straight:
            return (4, sorted_ranks)
        
        # 三条
        if 3 in rank_counts.values():
            three_rank = [r for r, count in rank_counts.items() if count == 3][0]
            kickers = sorted([r for r in ranks if r != three_rank], reverse=True)
            return (3, [three_rank] + kickers)
        
        # 两对
        pairs = [r for r, count in rank_counts.items() if count == 2]
        if len(pairs) == 2:
            pairs = sorted(pairs, reverse=True)
            kicker = [r for r in ranks if r not in pairs][0]
            return (2, pairs + [kicker])
        
        # 一对
        if len(pairs) == 1:
            pair_rank = pairs[0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return (1, [pair_rank] + kickers)
        
        # 高牌
        return (0, sorted_ranks)
    
    @staticmethod
    def _is_straight(ranks: List[int]) -> bool:
        """检查是否是顺子"""
        sorted_ranks = sorted(ranks)
        for i in range(len(sorted_ranks) - 1):
            if sorted_ranks[i + 1] - sorted_ranks[i] != 1:
                return False
        return True
    
    @staticmethod
    def hand_name(hand_type: int) -> str:
        """返回手牌类型名称"""
        names = {
            9: "皇家同花顺",
            8: "同花顺",
            7: "四条",
            6: "葫芦",
            5: "同花",
            4: "顺子",
            3: "三条",
            2: "两对",
            1: "一对",
            0: "高牌"
        }
        return names.get(hand_type, "未知")


class PokerCalculator:
    """德州扑克概率计算器"""
    
    def __init__(self):
        self.evaluator = HandEvaluator()
    
    def calculate_win_probability(self, 
                                  hole_cards: List[Card], 
                                  community_cards: List[Card],
                                  num_opponents: int = 1,
                                  num_simulations: int = 10000) -> Dict:
        """
        计算赢牌概率
        
        参数：
            hole_cards: 手牌（2张）
            community_cards: 公共牌（0-5张）
            num_opponents: 对手数量
            num_simulations: 模拟次数
        
        返回：
            包含赢率、平局率、输率的字典
        """
        wins = 0
        ties = 0
        losses = 0
        
        # 创建去除已知牌的牌堆
        deck = Deck()
        known_cards = hole_cards + community_cards
        deck.remove_cards(known_cards)
        
        # 需要发的公共牌数量
        cards_needed = 5 - len(community_cards)
        
        for _ in range(num_simulations):
            # 重置模拟牌堆
            sim_deck = Deck()
            sim_deck.remove_cards(known_cards)
            
            # 发剩余的公共牌
            if cards_needed > 0:
                remaining_community = sim_deck.draw(cards_needed)
            else:
                remaining_community = []
            
            full_community = community_cards + remaining_community
            
            # 更新模拟牌堆
            sim_deck.remove_cards(remaining_community)
            
            # 评估自己的手牌
            my_cards = hole_cards + full_community
            my_hand = self.evaluator.evaluate_hand(my_cards)
            
            # 模拟对手手牌
            opponent_hands = []
            for _ in range(num_opponents):
                opponent_hole = sim_deck.draw(2)
                opponent_cards = opponent_hole + full_community
                opponent_hand = self.evaluator.evaluate_hand(opponent_cards)
                opponent_hands.append(opponent_hand)
                sim_deck.remove_cards(opponent_hole)
            
            # 比较手牌
            best_opponent_hand = max(opponent_hands)
            
            if my_hand > best_opponent_hand:
                wins += 1
            elif my_hand == best_opponent_hand:
                ties += 1
            else:
                losses += 1
        
        return {
            'win_rate': wins / num_simulations,
            'tie_rate': ties / num_simulations,
            'loss_rate': losses / num_simulations,
            'simulations': num_simulations,
            'current_hand': self.evaluator.hand_name(self.evaluator.evaluate_hand(hole_cards + community_cards)[0])
        }
    
    def get_hand_strength(self, hole_cards: List[Card], community_cards: List[Card]) -> Tuple[int, str]:
        """获取当前手牌强度"""
        all_cards = hole_cards + community_cards
        if len(all_cards) >= 5:
            hand_type, _ = self.evaluator.evaluate_hand(all_cards)
            return hand_type, self.evaluator.hand_name(hand_type)
        else:
            return -1, "尚未形成完整手牌"
    
    def calculate_outs(self, hole_cards: List[Card], community_cards: List[Card]) -> Dict:
        """
        计算outs（能改进手牌的牌数）
        """
        if len(community_cards) >= 5:
            return {'outs': 0, 'description': '已经是河牌圈'}
        
        deck = Deck()
        known_cards = hole_cards + community_cards
        deck.remove_cards(known_cards)
        
        current_hand_type, _ = self.evaluator.evaluate_hand(hole_cards + community_cards)
        
        improving_cards = []
        for card in deck.cards:
            test_cards = hole_cards + community_cards + [card]
            new_hand_type, _ = self.evaluator.evaluate_hand(test_cards)
            if new_hand_type > current_hand_type:
                improving_cards.append(card)
        
        outs = len(improving_cards)
        
        # 计算下一张牌的改进概率
        remaining_cards = len(deck.cards)
        immediate_odds = (outs / remaining_cards) if remaining_cards > 0 else 0
        
        return {
            'outs': outs,
            'immediate_odds': immediate_odds,
            'improving_cards': improving_cards[:10],  # 只显示前10张
            'description': f'有{outs}张out牌可以改进手牌'
        }
