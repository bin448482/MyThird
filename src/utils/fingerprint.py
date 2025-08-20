"""
职位指纹生成工具

基于职位基本信息生成唯一指纹，用于去重检测
"""

import hashlib
import re
from typing import Optional


def generate_job_fingerprint(title: str, company: str, salary: str = "", location: str = "") -> str:
    """
    基于列表页可获取的信息生成职位指纹
    
    Args:
        title: 职位标题
        company: 公司名称  
        salary: 薪资信息（可选）
        location: 工作地点（可选）
        
    Returns:
        12位MD5哈希指纹
    """
    # 标准化处理
    title_clean = _normalize_text(title)
    company_clean = _normalize_text(company)
    salary_clean = _normalize_salary(salary) if salary else ""
    location_clean = _normalize_location(location) if location else ""
    
    # 生成指纹
    fingerprint_data = f"{title_clean}|{company_clean}|{salary_clean}|{location_clean}"
    return hashlib.md5(fingerprint_data.encode('utf-8')).hexdigest()[:12]


def _normalize_text(text: str) -> str:
    """
    标准化文本处理
    
    Args:
        text: 原始文本
        
    Returns:
        标准化后的文本
    """
    if not text:
        return ""
    
    # 转换为小写
    normalized = text.strip().lower()
    
    # 移除多余空格
    normalized = re.sub(r'\s+', '', normalized)
    
    # 移除常见的标点符号（保留关键信息）
    normalized = re.sub(r'[（）()【】\[\]《》<>""''""\'\']+', '', normalized)
    
    return normalized


def _normalize_salary(salary: str) -> str:
    """
    标准化薪资信息
    
    Args:
        salary: 原始薪资字符串
        
    Returns:
        标准化后的薪资
    """
    if not salary:
        return ""
    
    # 转换为小写并移除空格
    salary = salary.lower().replace(' ', '').replace('，', '-').replace(',', '-')
    
    # 提取数字范围
    numbers = re.findall(r'\d+', salary)
    if len(numbers) >= 2:
        # 如果有两个数字，认为是范围
        return f"{numbers[0]}-{numbers[1]}k"
    elif len(numbers) == 1:
        # 如果只有一个数字
        return f"{numbers[0]}k"
    
    return ""


def _normalize_location(location: str) -> str:
    """
    标准化地点信息
    
    Args:
        location: 原始地点字符串
        
    Returns:
        标准化后的地点
    """
    if not location:
        return ""
    
    # 转换为小写
    location = location.lower().strip()
    
    # 移除常见后缀
    suffixes = ['市', '区', '县', '省', '自治区', '特别行政区']
    for suffix in suffixes:
        location = location.replace(suffix, '')
    
    # 移除空格
    location = location.replace(' ', '')
    
    return location


def validate_fingerprint(fingerprint: str) -> bool:
    """
    验证指纹格式是否正确
    
    Args:
        fingerprint: 指纹字符串
        
    Returns:
        是否为有效指纹
    """
    if not fingerprint:
        return False
    
    # 检查长度
    if len(fingerprint) != 12:
        return False
    
    # 检查是否为十六进制字符
    try:
        int(fingerprint, 16)
        return True
    except ValueError:
        return False


def compare_job_similarity(job1: dict, job2: dict) -> float:
    """
    比较两个职位的相似度
    
    Args:
        job1: 职位1信息
        job2: 职位2信息
        
    Returns:
        相似度分数 (0-1)
    """
    # 提取关键字段
    title1 = _normalize_text(job1.get('title', ''))
    title2 = _normalize_text(job2.get('title', ''))
    company1 = _normalize_text(job1.get('company', ''))
    company2 = _normalize_text(job2.get('company', ''))
    
    # 计算相似度
    title_similarity = _text_similarity(title1, title2)
    company_similarity = _text_similarity(company1, company2)
    
    # 加权平均（标题权重更高）
    overall_similarity = title_similarity * 0.7 + company_similarity * 0.3
    
    return overall_similarity


def _text_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度
    
    Args:
        text1: 文本1
        text2: 文本2
        
    Returns:
        相似度分数 (0-1)
    """
    if not text1 or not text2:
        return 0.0
    
    if text1 == text2:
        return 1.0
    
    # 简单的字符级相似度计算
    # 可以后续升级为更复杂的算法（如编辑距离）
    common_chars = set(text1) & set(text2)
    total_chars = set(text1) | set(text2)
    
    if not total_chars:
        return 0.0
    
    return len(common_chars) / len(total_chars)


def extract_job_key_info(job_data: dict) -> dict:
    """
    从职位数据中提取关键信息用于指纹生成
    
    Args:
        job_data: 职位数据字典
        
    Returns:
        包含关键信息的字典
    """
    return {
        'title': job_data.get('title', ''),
        'company': job_data.get('company', ''),
        'salary': job_data.get('salary', ''),
        'location': job_data.get('location', ''),
        'fingerprint': generate_job_fingerprint(
            job_data.get('title', ''),
            job_data.get('company', ''),
            job_data.get('salary', ''),
            job_data.get('location', '')
        )
    }


def is_duplicate_job(job1: dict, job2: dict, threshold: float = 0.9) -> bool:
    """
    判断两个职位是否为重复职位
    
    Args:
        job1: 职位1
        job2: 职位2
        threshold: 相似度阈值
        
    Returns:
        是否为重复职位
    """
    # 首先检查指纹
    fingerprint1 = job1.get('job_fingerprint') or generate_job_fingerprint(
        job1.get('title', ''), job1.get('company', ''),
        job1.get('salary', ''), job1.get('location', '')
    )
    fingerprint2 = job2.get('job_fingerprint') or generate_job_fingerprint(
        job2.get('title', ''), job2.get('company', ''),
        job2.get('salary', ''), job2.get('location', '')
    )
    
    if fingerprint1 == fingerprint2:
        return True
    
    # 如果指纹不同，进一步检查相似度
    similarity = compare_job_similarity(job1, job2)
    return similarity >= threshold