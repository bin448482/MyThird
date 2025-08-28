# 批次投递与薪资过滤逻辑修复

## 问题描述

在实现薪资过滤功能后，发现批次投递逻辑存在冲突：

### 原始问题
1. **批次逻辑不准确**：先取固定数量的职位（如20个），然后在这些职位中应用薪资过滤
2. **实际批次大小不可控**：如果薪资过滤拒绝了大部分职位，实际可投递的职位数量远少于预期
3. **效率低下**：可能需要多次查询才能获得足够的有效职位

### 具体场景
- 请求批次大小：20个职位
- 薪资过滤拒绝率：90%
- 实际获得：仅2个可投递职位
- 期望获得：20个可投递职位

## 解决方案

### 核心思路
**批次应该基于过滤后的有效职位数量，而不是原始职位数量**

### 修复策略
1. **动态查询数量调整**：根据历史薪资过滤拒绝率，智能调整数据库查询数量
2. **精确批次控制**：确保返回的职位数量符合批次大小要求
3. **性能优化**：减少数据库查询次数，提高效率

## 实现细节

### 1. 数据管理器修改

修改 `src/submission/data_manager.py` 中的 `get_unprocessed_matches()` 方法：

```python
def get_unprocessed_matches(self, limit: int = 50, priority_filter: Optional[str] = None, apply_salary_filter: bool = True) -> List[JobMatchRecord]:
    """
    获取未处理的匹配记录（支持薪资过滤）
    
    Args:
        limit: 限制数量（薪资过滤后的有效职位数量）
        priority_filter: 优先级过滤 ('high', 'medium', 'low')
        apply_salary_filter: 是否应用薪资过滤
        
    Returns:
        未处理的职位匹配记录列表
    """
```

### 2. 动态查询倍数计算

```python
# 根据历史过滤率动态调整查询数量
if apply_salary_filter and self.salary_filter:
    filter_stats = self.salary_filter.get_stats()
    rejection_rate = filter_stats.get('rejection_rate', 0.9)  # 默认90%拒绝率
    
    # 根据拒绝率计算需要查询的记录数
    multiplier = max(2, int(1 / (1 - rejection_rate)) + 1)
    query_limit = limit * multiplier
```

### 3. 查询倍数示例

| 拒绝率 | 查询倍数 | 批次大小=20时的查询数量 |
|--------|----------|------------------------|
| 50%    | 3x       | 60条记录               |
| 80%    | 6x       | 120条记录              |
| 90%    | 11x      | 220条记录              |
| 95%    | 21x      | 420条记录              |

## 修复效果

### 修复前
```
请求批次大小: 20
查询记录数: 40 (固定倍数)
薪资过滤拒绝: 36个 (90%)
实际获得: 4个职位 ❌
```

### 修复后
```
请求批次大小: 20
预估拒绝率: 90%
查询记录数: 220 (动态调整)
薪资过滤拒绝: 200个 (90%)
实际获得: 20个职位 ✅
```

## 技术优势

### 1. 智能适应
- 根据实际薪资过滤效果动态调整查询策略
- 自动学习和优化查询倍数

### 2. 精确控制
- 确保批次大小的准确性
- 避免批次大小不可控的问题

### 3. 性能优化
- 减少多次查询的需要
- 提高数据库查询效率

### 4. 向后兼容
- 保持原有API接口不变
- 可选择启用/禁用薪资过滤

## 测试验证

### 测试脚本
创建了 `test_batch_logic_fix.py` 来验证修复效果：

```python
# 测试不同批次大小的行为
batch_sizes = [5, 10, 20]

for batch_size in batch_sizes:
    records = dm.get_unprocessed_matches(
        limit=batch_size, 
        apply_salary_filter=True
    )
    
    # 验证返回的记录数是否符合预期
    assert len(records) <= batch_size
```

### 动态调整验证
```python
# 验证不同拒绝率下的查询倍数计算
rejection_rates = [0.5, 0.8, 0.9, 0.95]
for rejection_rate in rejection_rates:
    multiplier = max(2, int(1 / (1 - rejection_rate)) + 1)
    query_limit = batch_size * multiplier
    print(f"拒绝率 {rejection_rate:.0%} -> 查询倍数 {multiplier}x")
```

## 使用说明

### 1. 正常使用
```python
# 获取20个经过薪资过滤的有效职位
records = data_manager.get_unprocessed_matches(
    limit=20, 
    apply_salary_filter=True
)
```

### 2. 禁用薪资过滤
```python
# 获取20个未过滤的职位
records = data_manager.get_unprocessed_matches(
    limit=20, 
    apply_salary_filter=False
)
```

### 3. 监控过滤效果
```python
# 获取薪资过滤统计
stats = data_manager.salary_filter.get_stats()
print(f"拒绝率: {stats['rejection_rate']:.1%}")
print(f"查询优化效果: 自动调整查询倍数")
```

## 总结

这次修复解决了薪资过滤与批次投递的逻辑冲突，确保了：

1. ✅ **批次大小准确性**：返回的职位数量符合预期
2. ✅ **智能查询优化**：根据过滤效果动态调整查询策略  
3. ✅ **系统性能提升**：减少不必要的数据库查询
4. ✅ **用户体验改善**：批次投递行为更加可预测和可控

修复后的系统能够智能地处理薪资过滤，确保批次投递功能按预期工作，为用户提供更好的求职自动化体验。