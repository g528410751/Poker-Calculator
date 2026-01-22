"""
德州扑克概率计算器 - Streamlit 应用
"""
import streamlit as st
import os
from dotenv import load_dotenv
from poker_calculator import Card, PokerCalculator
from deepseek_advisor import DeepSeekAdvisor

# 加载 .env 文件
load_dotenv()

# 页面配置
st.set_page_config(
    page_title="德州扑克概率计算器",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card-display {
        font-size: 2rem;
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin: 10px 0;
    }
    /* 统一卡牌按钮样式 */
    div[data-testid="stButton"] button {
        min-width: 32px !important;
        padding: 6px 4px !important;
        font-size: 0.85rem !important;
        white-space: nowrap !important;
    }
    div[data-testid="stColumn"] {
        padding: 2px !important;
    }
</style>
""", unsafe_allow_html=True)

# 使用 components.html 注入 JavaScript 来设置红色花色按钮的文字颜色
import streamlit.components.v1 as components
components.html("""
<script>
function colorCardButtons() {
    const buttons = parent.document.querySelectorAll('button[kind="secondary"] p, button[data-testid="stBaseButton-secondary"] p');
    buttons.forEach(p => {
        const text = p.textContent || '';
        if (text.includes('♥') || text.includes('♦')) {
            p.style.color = '#d32f2f';
        }
    });
}
// 延迟执行以确保DOM加载完成
setTimeout(colorCardButtons, 100);
setTimeout(colorCardButtons, 500);
setTimeout(colorCardButtons, 1000);
// 监听DOM变化
const observer = new MutationObserver(() => {
    setTimeout(colorCardButtons, 50);
});
observer.observe(parent.document.body, { childList: true, subtree: true });
</script>
""", height=0)

# 初始化session state
if 'calculator' not in st.session_state:
    st.session_state.calculator = PokerCalculator()

if 'advisor' not in st.session_state:
    st.session_state.advisor = None

if 'selected_hole_cards' not in st.session_state:
    st.session_state.selected_hole_cards = []

if 'selected_community_cards' not in st.session_state:
    st.session_state.selected_community_cards = []


# 帮助信息定义
HELP_TEXTS = {
    "win_rate": "赢牌概率：通过蒙特卡洛模拟计算的在当前情况下击败所有对手的概率",
    "tie_rate": "平局概率：与对手形成相同牌力平分底池的概率",
    "loss_rate": "输牌概率：被对手击败的概率",
    "pot_odds": "底池赔率：跟注金额/(底池+跟注金额)，表示跟注需要的最低赢率",
    "equity": "权益/财率：你在当前底池中应得的份额比例，等同于赢牌概率",
    "ev": "期望值(EV)：长期来看每次做相同决策的平均收益，正值表示盈利",
    "outs": "Out牌：能够改进你手牌的剩余牌的数量",
    "rule_of_4": "四倍法则：翻牌圈时，Outs数×4≈到河牌时的改进概率",
    "rule_of_2": "二倍法则：转牌圈时，Outs数×2≈到河牌时的改进概率",
    "spr": "SPR(有效筹码比)：你的筹码/底池，用于判断深筹码还是浅筹码打法"
}


def create_card_grid(label: str, card_type: str, max_cards: int):
    """创建表格形式的卡牌选择器"""
    st.subheader(label)
    
    # 获取所有已选牌（用于禁用重复选择）
    hole_set = set(f"{c.rank}{c.suit}" for c in st.session_state.selected_hole_cards)
    community_set = set(f"{c.rank}{c.suit}" for c in st.session_state.selected_community_cards)
    
    if card_type == "hole":
        current_set = hole_set
        other_set = community_set
    else:
        current_set = community_set
        other_set = hole_set
    
    # 显示当前选中的牌
    if current_set:
        st.markdown("**已选择:**")
        selected_list = sorted(list(current_set))  # 排序保持稳定
        cols = st.columns(min(len(selected_list), 7))
        for i, card_str in enumerate(selected_list[:7]):
            with cols[i]:
                suit = card_str[-1]
                rank = card_str[:-1]
                suit_color = "#d32f2f" if suit in ['♥', '♦'] else "#212121"
                st.markdown(
                    f"<div style='font-size:1.5rem; text-align:center; color:{suit_color}; "
                    f"background:#f0f2f6; border-radius:8px; padding:8px; white-space:nowrap;'>"
                    f"{rank}{suit}</div>", 
                    unsafe_allow_html=True
                )
    else:
        st.caption(f"请在下方点击选择牌（最多{max_cards}张）")
    
    # 创建表格形式的牌选择器
    st.markdown("##### 点击选牌:")
    
    for suit in Card.SUITS:
        is_red = suit in ['♥', '♦']
        suit_color = "#d32f2f" if is_red else "#212121"
        
        cols = st.columns(13)
        
        for j, rank in enumerate(Card.RANKS):
            card_str = f"{rank}{suit}"
            is_selected = card_str in current_set
            is_other_selected = card_str in other_set
            can_add = len(current_set) < max_cards
            
            with cols[j]:
                if is_other_selected:
                    # 已被其他位置选中，显示为灰色不可点击
                    st.markdown(
                        f"<div style='text-align:center; padding:6px 2px; background:#e0e0e0; "
                        f"border-radius:6px; color:#9e9e9e; font-size:0.85rem; opacity:0.5; "
                        f"white-space:nowrap;'>{rank}{suit}</div>",
                        unsafe_allow_html=True
                    )
                elif is_selected:
                    # 已选中状态 - 使用 primary 类型按钮（白色文字）
                    if st.button(f"{rank}{suit}", key=f"{card_type}_{rank}_{suit}", 
                                 help="点击取消选择", use_container_width=True, type="primary"):
                        # 移除这张牌
                        if card_type == "hole":
                            st.session_state.selected_hole_cards = [
                                c for c in st.session_state.selected_hole_cards 
                                if f"{c.rank}{c.suit}" != card_str
                            ]
                        else:
                            st.session_state.selected_community_cards = [
                                c for c in st.session_state.selected_community_cards 
                                if f"{c.rank}{c.suit}" != card_str
                            ]
                        st.rerun()
                else:
                    # 未选中状态 - 按钮
                    btn_key = f"{card_type}_{rank}_{suit}"
                    clicked = st.button(f"{rank}{suit}", key=btn_key,
                                 help="点击选择" if can_add else f"已达到{max_cards}张上限",
                                 disabled=not can_add, use_container_width=True)
                    if clicked:
                        # 添加这张牌
                        if card_type == "hole":
                            st.session_state.selected_hole_cards.append(Card(rank, suit))
                        else:
                            st.session_state.selected_community_cards.append(Card(rank, suit))
                        st.rerun()
    
    # 获取当前选中的牌列表
    if card_type == "hole":
        cards = st.session_state.selected_hole_cards
    else:
        cards = st.session_state.selected_community_cards
    
    # 清空按钮
    if cards:
        if st.button(f"🗑️ 清空", key=f"clear_{card_type}"):
            if card_type == "hole":
                st.session_state.selected_hole_cards = []
            else:
                st.session_state.selected_community_cards = []
            st.rerun()
    
    return cards


def display_cards(cards, title):
    """显示卡牌"""
    if cards:
        card_strs = []
        for card in cards:
            color = "red" if card.suit in ['♥', '♦'] else "black"
            card_strs.append(f"<span style='color:{color}; font-size:1.5rem; margin:5px;'>{card.rank}{card.suit}</span>")
        st.markdown(f"**{title}:** {''.join(card_strs)}", unsafe_allow_html=True)


def main():
    # 标题
    st.markdown("<div class='main-header'>🎴 德州扑克概率计算器 & AI 决策助手</div>", unsafe_allow_html=True)
    
    # 侧边栏 - API配置
    with st.sidebar:
        st.header("⚙️ 配置")
        
        # DeepSeek API配置
        st.subheader("DeepSeek API")
        
        # 检查是否有开发者默认API
        default_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        has_default_api = bool(default_api_key)
        
        # 用户选择是否使用自己的API
        use_custom_api = st.checkbox(
            "使用自己的 API Key",
            value=False,
            help="勾选后可以输入你自己的 DeepSeek API Key"
        )
        
        if use_custom_api:
            # 用户输入自己的API
            custom_api_key = st.text_input(
                "API Key",
                type="password",
                value="",
                help="输入你的 DeepSeek API Key"
            )
            api_key = custom_api_key if custom_api_key else None
        else:
            # 使用默认API
            api_key = default_api_key
        
        # 初始化API客户端
        if api_key:
            try:
                if st.session_state.advisor is None or st.session_state.get('api_key') != api_key:
                    st.session_state.advisor = DeepSeekAdvisor(api_key)
                    st.session_state.api_key = api_key
                if use_custom_api:
                    st.success("✅ 你的 API 已连接")
                else:
                    st.success("✅ AI 功能已就绪")
            except Exception as e:
                st.error(f"❌ API 连接失败: {str(e)}")
        else:
            if use_custom_api:
                st.warning("⚠️ 请输入你的 API Key")
            else:
                st.warning("⚠️ AI 决策功能不可用")
        
        st.divider()
        
        # 计算参数
        st.subheader("计算参数")
        num_opponents = st.slider(
            "对手数量",
            min_value=1,
            max_value=9,
            value=1,
            help="参与游戏的对手数量"
        )
        
        num_simulations = st.select_slider(
            "模拟次数",
            options=[1000, 2000, 3000, 4000, 5000],
            value=3000,
            help="蒙特卡洛模拟次数，越多越准确但计算时间越长"
        )
        
        st.divider()
        
        # 筹码和底池信息
        st.subheader("筹码信息")
        pot_size = st.number_input(
            "当前底池",
            min_value=0.0,
            value=100.0,
            step=10.0
        )
        
        current_bet = st.number_input(
            "需要跟注",
            min_value=0.0,
            value=20.0,
            step=5.0
        )
        
        your_stack = st.number_input(
            "你的筹码",
            min_value=0.0,
            value=500.0,
            step=10.0
        )
        
        position = st.selectbox(
            "你的位置",
            options=["早位", "中位", "晚位", "小盲", "大盲", "庄位"]
        )
    
    # 主界面
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📋 选择你的牌")
        
        # 手牌输入 - 使用新的卡牌网格
        hole_cards = create_card_grid("🃏 手牌（2张）", "hole", max_cards=2)
        
        st.divider()
        
        # 游戏阶段选择
        stage = st.radio(
            "🎴 游戏阶段",
            options=["翻牌前", "翻牌圈(3张)", "转牌圈(4张)", "河牌圈(5张)"],
            horizontal=True,
            key="game_stage"
        )
        
        num_cards_map = {
            "翻牌前": 0,
            "翻牌圈(3张)": 3,
            "转牌圈(4张)": 4,
            "河牌圈(5张)": 5
        }
        max_community = num_cards_map[stage]
        
        # 公共牌输入
        if max_community > 0:
            community_cards = create_card_grid(f"🎴 公共牌（{max_community}张）", "community", max_cards=max_community)
        else:
            community_cards = []
            st.session_state.selected_community_cards = []
            st.info("翻牌前无公共牌")
    
    with col2:
        st.header("📊 当前牌面")
        
        # 显示当前牌
        if hole_cards:
            display_cards(hole_cards, "手牌")
        else:
            st.info("请在左侧选择你的手牌")
        
        if community_cards:
            display_cards(community_cards, "公共牌")
        
        # 显示当前手牌类型
        if len(hole_cards) == 2:
            hand_type, hand_name = st.session_state.calculator.get_hand_strength(
                hole_cards, community_cards
            )
            if hand_type >= 0:
                st.markdown(f"### 当前手牌: **{hand_name}**")
    
    # 检查重复牌
    all_cards = hole_cards + community_cards
    card_set = set((c.rank, c.suit) for c in all_cards)
    has_duplicate = len(card_set) < len(all_cards)
    
    if has_duplicate:
        st.error("❌ 检测到重复的牌！每张牌只能使用一次。")
    
    # 计算按钮 - 合并所有功能
    st.divider()
    
    analyze_button = st.button("🎲 全面分析（概率 + Outs + AI决策）", use_container_width=True, 
                               disabled=has_duplicate)
    
    # 全面分析
    if analyze_button:
        if len(hole_cards) != 2:
            st.error("❌ 请选择完整的2张手牌")
        else:
            st.divider()
            
            # 1. 计算概率
            with st.spinner("正在计算赢牌概率..."):
                result = st.session_state.calculator.calculate_win_probability(
                    hole_cards,
                    community_cards,
                    num_opponents=num_opponents,
                    num_simulations=num_simulations
                )
            
            # 显示概率结果
            st.subheader("📊 概率分析")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("赢牌概率", f"{result['win_rate']:.1%}", help=HELP_TEXTS["win_rate"])
            with col2:
                st.metric("平局概率", f"{result['tie_rate']:.1%}", help=HELP_TEXTS["tie_rate"])
            with col3:
                st.metric("输牌概率", f"{result['loss_rate']:.1%}", help=HELP_TEXTS["loss_rate"])
            
            # 底池赔率分析 - 修复逻辑
            st.subheader("💰 底池赔率分析")
            
            if current_bet > 0:
                # 需要跟注的情况
                pot_odds = current_bet / (pot_size + current_bet)
                ev = result['win_rate'] * pot_size - (1 - result['win_rate']) * current_bet
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("跟注所需最低赢率", f"{pot_odds:.1%}", help=HELP_TEXTS["pot_odds"])
                with col2:
                    st.metric("你的权益(Equity)", f"{result['win_rate']:.1%}", help=HELP_TEXTS["equity"])
                with col3:
                    st.metric("期望值(EV)", f"{ev:+.1f}", help=HELP_TEXTS["ev"])
                
                # 判断跟注是否有利
                equity_vs_odds = result['win_rate'] - pot_odds
                if equity_vs_odds > 0.1:  # 赢率比底池赔率高10%以上
                    st.success(f"✅ 非常有利！权益 {result['win_rate']:.1%} >> 所需赢率 {pot_odds:.1%}，建议加注")
                elif equity_vs_odds > 0:
                    st.success(f"✅ 有利可图！权益 {result['win_rate']:.1%} > 所需赢率 {pot_odds:.1%}")
                else:
                    st.warning(f"⚠️ 跟注不利！权益 {result['win_rate']:.1%} < 所需赢率 {pot_odds:.1%}，考虑弃牌或诈唬")
            else:
                # 不需要跟注的情况（大盲位置或无人加注）
                st.success(f"✅ 无需跟注，你的赢率为 {result['win_rate']:.1%}，可以免费看牌或主动加注")
            
            # 2. 计算 Outs
            outs_info = ""
            if len(community_cards) > 0 and len(community_cards) < 5:
                st.subheader("🎯 Outs 分析")
                outs_result = st.session_state.calculator.calculate_outs(
                    hole_cards,
                    community_cards
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Out 牌数量", f"{outs_result['outs']} 张", help=HELP_TEXTS["outs"])
                with col2:
                    st.metric("下张牌改进概率", f"{outs_result['immediate_odds']:.1%}")
                with col3:
                    if len(community_cards) == 3:  # 翻牌圈
                        river_odds = min(outs_result['outs'] * 4, 100) / 100
                        st.metric("到河牌改进", f"{river_odds:.1%}", help=HELP_TEXTS["rule_of_4"])
                    elif len(community_cards) == 4:  # 转牌圈
                        river_odds = min(outs_result['outs'] * 2, 100) / 100
                        st.metric("到河牌改进", f"{river_odds:.1%}", help=HELP_TEXTS["rule_of_2"])
                
                if outs_result['improving_cards']:
                    improving_str = ' '.join([str(card) for card in outs_result['improving_cards']])
                    st.caption(f"部分改进牌: {improving_str}")
                
                outs_info = f"{outs_result['outs']}张, 改进率{outs_result['immediate_odds']:.1%}"
            
            # 3. AI决策建议
            if st.session_state.advisor is not None:
                st.subheader("🤖 AI 决策建议")
                game_stage = st.session_state.get('game_stage', '翻牌前')
                
                response_placeholder = st.empty()
                full_response = ""
                
                for chunk in st.session_state.advisor.get_decision_stream(
                    hole_cards=hole_cards,
                    community_cards=community_cards,
                    pot_size=pot_size,
                    current_bet=current_bet,
                    your_stack=your_stack,
                    position=position,
                    num_opponents=num_opponents,
                    win_probability=result['win_rate'],
                    current_hand=result['current_hand'],
                    game_stage=game_stage,
                    outs_info=outs_info
                ):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
            else:
                st.info("💡 配置 DeepSeek API Key 后可获取 AI 决策建议")
    
    # 页脚
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>💡 提示: 本工具仅供学习和娱乐使用，请理性游戏</p>
        <p>🔗 使用 DeepSeek AI 提供智能决策建议</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
