# GDD Template

Copy this for new games. Fill in `<PLACEHOLDERS>`.

---

# Game Design Document: <TITLE>

**Version**: 1.0  **Date**: <DATE>  **Genre**: <GENRE>

## 1. Executive Summary
<One paragraph: what the game IS, who it's FOR, why it's FUN>

## 2. Target Audience
- **Primary Player Type**: <Achiever/Explorer/Socializer/Killer>
- **Age Range**: <X+>
- **Play Session**: <N min>

## 3. Core Loops
### 30s: <immediate action>
### 5min: <challenge cycle>
### 30min: <progression goal>

## 4. MDA
**M**: <list mechanics>  
**D**: <emergent behaviour>  
**A**: <primary emotion>

## 5. Generate Command
```python
gen.generate(title="<TITLE>", genre="<genre>", player_class="<class>",
             enemies=<N>, props=<M>, level_size=<S>)
```

## 6. Win / Loss
- **Win**: <condition>
- **Loss**: HP ≤ 0
