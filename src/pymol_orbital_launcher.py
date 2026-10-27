#!/usr/bin/env python3
# interactive_pymol_setup.py
import os
import subprocess
import argparse

def interactive_setup():
    """交互式配置参数"""
    
    print("PyMOL轨道可视化设置")
    print("=" * 40)
    
    # 获取cube文件
    cube_file = input("输入cube文件路径 [orbital.cube]: ").strip()
    if not cube_file:
        cube_file = "orbital.cube"
    
    # 检查文件是否存在
    if not os.path.exists(cube_file):
        print(f"错误: 文件 {cube_file} 不存在!")
        return None
    
    # 获取结构文件
    structure_file = input("输入分子结构文件路径 [回车跳过]: ").strip()
    if structure_file and not os.path.exists(structure_file):
        print(f"警告: 结构文件 {structure_file} 不存在，将跳过")
        structure_file = None
    
    # 获取等值面水平
    level_input = input("输入等值面水平 [0.035]: ").strip()
    level = float(level_input) if level_input else 0.035
    
    # 颜色选择
    print("\n选择颜色方案:")
    print("1. 蓝/红 (默认)")
    print("2. 青/洋红") 
    print("3. 绿/黄")
    color_choice = input("选择 [1]: ").strip() or "1"
    
    color_schemes = {
        "1": ("blue", "red"),
        "2": ("cyan", "magenta"), 
        "3": ("green", "yellow")
    }
    pos_color, neg_color = color_schemes.get(color_choice, ("blue", "red"))
    
    return {
        'cube_file': cube_file,
        'structure_file': structure_file,
        'level': level,
        'pos_color': pos_color,
        'neg_color': neg_color
    }

def generate_pymol_script(params):
    """生成PyMOL脚本"""
    
    script = f"""
# 自动生成的PyMOL轨道可视化脚本
# Cube文件: {params['cube_file']}

# 基本设置
set surface_quality, 1
set surface_mode, 1
set transparency, 0.4
bg white
set depth_cue, 0
set antialias, 2

# 加载分子结构
"""
    
    if params['structure_file']:
        script += f"""
load {params['structure_file']}, molecule
show sticks, molecule
util.cbaw molecule
hide lines, molecule
"""
    
    script += f"""
# 加载和显示轨道
load {params['cube_file']}, orbital
isosurface orbital_pos, orbital, level={params['level']}
isosurface orbital_neg, orbital, level=-{params['level']}
color {params['pos_color']}, orbital_pos
color {params['neg_color']}, orbital_neg
set transparency, 0.4

# 视图调整
orient
zoom complete=1
reset
ray 1200, 800

print("=== 轨道可视化完成 ===")
print("文件: {params['cube_file']}")
print("等值面水平: ±{params['level']}")
print("颜色: {params['pos_color']} / {params['neg_color']}")
print("=== 控制命令 ===")
print("hide surface orbital_pos/neg - 隐藏轨道")
print("show surface orbital_pos/neg - 显示轨道") 
print("set surface_quality, 2 - 提高质量")
print("volume_level orbital, 0.01 - 调整等值面")
"""
    
    script_file = "interactive_orbital_view.pml"
    with open(script_file, 'w') as f:
        f.write(script)
    
    return script_file

def main():
    # 交互式配置
    params = interactive_setup()
    if not params:
        return
    
    # 生成脚本
    script_file = generate_pymol_script(params)
    print(f"\nPyMOL脚本已生成: {script_file}")
    
    # 启动PyMOL
    launch = input("\n是否现在启动PyMOL? [Y/n]: ").strip().lower()
    if launch in ['', 'y', 'yes']:
        print("启动PyMOL...")
        subprocess.run(['pymol', script_file])
    else:
        print(f"可以稍后使用命令启动: pymol {script_file}")

if __name__ == "__main__":
    main()
