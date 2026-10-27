#!/usr/bin/env python3
import numpy as np
import sys, os
import argparse
from scipy import ndimage
import matplotlib.pyplot as plt

class STMDataProcessor:
    """
    STM数据处理和可视化类
    """
    
    def __init__(self, filename=None):
        """
        初始化STM数据处理器
        
        Parameters:
        filename (str): 数据文件路径
        """
        self.data = {}
        if filename:
            self.load_data(filename)
    
    def load_data(self, filename):
        """
        从文件加载数据
        
        Parameters:
        filename (str): 数据文件路径
        """
        if not os.path.isfile(filename):
            print(f"Error: not find input file: {filename}")
            return False
        
        self.data = self.import_from_mtd(filename)
        print("Loaded data keys:", list(self.data.keys()))
        return True
    
    def import_from_mtd(self, filename):
        """
        从mtd格式文件导入数据
        
        Parameters:
        filename (str): 数据文件路径
        
        Returns:
        dict: 处理后的STM数据字典
        """
        STM_Dict = {}
        with open(filename, 'r') as f:
            lines = f.readlines()
            tmp_tag = 'blank'
            STM_Dict[tmp_tag] = []
            for line in lines:
                if line.strip() and line.strip()[0] != '%':
                    if "=[" in line:
                        tmp_list = line.split("=[")
                        tmp_tag = tmp_list[0]
                        STM_Dict[tmp_tag] = []
                        STM_Dict[tmp_tag].append([float(x) for x in tmp_list[1].split()])
                        print(f"Import {tmp_tag}")
                    elif "];" in line:
                        tmp_list = line.split("];")
                        STM_Dict[tmp_tag].append([float(x) for x in tmp_list[0].split()])
                        #print(f"close {tmp_tag} tag ({len(STM_Dict[tmp_tag])})")
                        tmp_tag = 'blank'
                    else:
                        try:
                            STM_Dict[tmp_tag].append([float(x) for x in line.split()])
                        except:
                            print(f"%s" %line.strip())
        
        STM_Dict.pop('blank', None)
        
        # 转换数据格式
        for key in STM_Dict.keys():
            if key == "X" or key == "Y":
                STM_Dict[key] = self.convert_to_2d_array(STM_Dict[key])
            else:
                STM_Dict[key] = self.convert_to_2d_array(STM_Dict[key])
                STM_Dict[key] = STM_Dict[key] * STM_Dict[key]  # 平方处理
        
        return STM_Dict
    
    def add_mixed_data(self, mix_configs):
        """
        添加混合数据
        
        Parameters:
        mix_configs (list): 混合配置列表，每个配置为 [name, data1, data2, ...]
        """
        for mix_config in mix_configs:
            if len(mix_config) < 3:
                print(f"警告: 混合配置 '{mix_config}' 需要至少3个参数 [名称, 数据1, 数据2, ...]")
                continue
            
            mix_name = mix_config[0]
            data_keys = mix_config[1:]
            
            # 检查所有数据键是否存在
            missing_keys = [key for key in data_keys if key not in self.data]
            if missing_keys:
                print(f"警告: 无法创建混合数据 '{mix_name}'，缺少数据: {missing_keys}")
                continue
            
            # 创建混合数据（所有数据相加）
            mixed_data = np.zeros_like(self.data[data_keys[0]])
            for key in data_keys:
                mixed_data += self.data[key]
            
            self.data[mix_name] = mixed_data
            print(f"创建混合数据: {mix_name} = {' + '.join(data_keys)}")
    
    def convert_to_2d_array(self, dvec):
        """
        将列表转换为2D numpy数组
        
        Parameters:
        dvec (list): 二维列表
        
        Returns:
        numpy.ndarray: 2D数组
        """
        dim1 = len(dvec)
        dim2 = len(dvec[0])
        
        # 检查所有子列表长度是否一致
        for x in dvec:
            if len(x) != dim2:
                print("Error: dvec cannot be converted to a 2d-array, because the sub-vectors have different dimension")
                return None
        
        try:
            Z = np.array(dvec)
            print(f"直接转换后的形状: {Z.shape}")
        except:
            # 如果失败，使用展平方法
            flat_list = [item for sublist in dvec for item in sublist]
            Z = np.array(flat_list).reshape(dim1, dim2)
        
        return Z
    
    def process_data(self, sigma=1, zoom_factor=8, order=3, plotkeys=None):
        """
        处理数据（高斯平滑和插值）
        
        Parameters:
        sigma (float): 高斯滤波的sigma值
        zoom_factor (int): 缩放因子
        order (int): 插值阶数
        plotkeys: 需要处理的数据名称列表
        
        Returns:
        dict: 处理后的数据
        """
        processed_data = {}
        processed_data['X'] = self.data['X']
        processed_data['Y'] = self.data['Y']
        
        if not plotkeys:
            plotkeys = self.generate_plot_keys()
        
        for key in plotkeys:
            value = self.data[key]
            # 高斯平滑
            data_smooth = ndimage.gaussian_filter(value, sigma=sigma)
            # 插值
            processed_data[key] = ndimage.zoom(data_smooth, zoom_factor, order=order)
        
        return processed_data
    
    def plot_all(self, cmap='plasma', sigma=1, zoom_factor=8, order=3, 
                 save_fig=True, show_fig=False, plotkeys=None, dpi=300, figsize=(8, 6)):
        """
        绘制所有数据的图像
        
        Parameters:
        cmap (str): 颜色映射
        sigma (float): 高斯滤波的sigma值
        zoom_factor (int): 缩放因子
        order (int): 插值阶数
        save_fig (bool): 是否保存图像
        show_fig (bool): 是否显示图像
        plotkeys (str list): 用于制图的数据key列表
        dpi (int): 图像分辨率
        figsize (tuple): 图像尺寸
        """
        if not self.data:
            print("No data loaded. Please load data first.")
            return

        processed_data = self.process_data(sigma, zoom_factor, order, plotkeys=plotkeys)

        #print("debug 1")

        for key, value in self.data.items():
            if key in plotkeys:
                #print(f"debug 1a-{key}")
                self.plot_single(key, processed_data[key], cmap,
                               vmin=value.min(), vmax=value.max(), 
                               save_fig=save_fig, show_fig=show_fig,
                               dpi=dpi, figsize=figsize)
                #print(f"debug 1b-{key}")
        #print("debug 2")
    
    def plot_single(self, key, data, cmap='plasma', vmin=None, vmax=None, 
                   save_fig=True, show_fig=False, dpi=300, figsize=(8, 6)):
        """
        绘制单个数据图像
        
        Parameters:
        key (str): 数据键名
        data (numpy.ndarray): 数据数组
        cmap (str): 颜色映射
        vmin (float): 颜色范围最小值
        vmax (float): 颜色范围最大值
        save_fig (bool): 是否保存图像
        show_fig (bool): 是否显示图像
        dpi (int): 图像分辨率
        figsize (tuple): 图像尺寸
        """
        plt.figure(figsize=figsize)
        
        # 绘制图像
        plt.pcolormesh(data, shading='auto', cmap=cmap, vmin=vmin, vmax=vmax)
        
        plt.colorbar(label=key)
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title(f'STM image - {key}')
        
        if save_fig:
            plt.savefig(f"{key}.png", dpi=dpi, bbox_inches='tight')
            print(f"Saved: {key}.png")
        
        if show_fig:
            plt.show()
        else:
            plt.close()
    
    def get_data_keys(self):
        """
        获取数据键名列表
        
        Returns:
        list: 数据键名列表
        """
        return list(self.data.keys())
    
    def get_data_shape(self, key):
        """
        获取指定数据的形状
        
        Parameters:
        key (str): 数据键名
        
        Returns:
        tuple: 数据形状
        """
        if key in self.data:
            return self.data[key].shape
        else:
            print(f"Key '{key}' not found in data.")
            return None
    
    def summary(self):
        """
        打印数据摘要
        """
        if not self.data:
            print("No data loaded.")
            return
        
        print("=" * 50)
        print("STM Data Summary")
        print("=" * 50)
        print(f"Total datasets: {len(self.data)}")
        print("Data keys:", list(self.data.keys()))
        
        for key, value in self.data.items():
            print(f"{key}: shape {value.shape}, range [{value.min():.4f}, {value.max():.4f}]")
        print("=" * 50)

    def generate_plot_keys(self, plotkeys=None):
        """
        生成用于制图的数据Keys列表
        """
        if plotkeys:
            # 如果 plotkeys 是列表的列表（来自 argparse），则展平它
            if isinstance(plotkeys, list) and len(plotkeys) > 0 and isinstance(plotkeys[0], list):
                plotkeys = plotkeys[0]
            
            for key in plotkeys:
                print(f"检查数据键: {key}")
                if key not in self.data:
                    raise ValueError(f"没有名为 '{key}' 的数据可用于画图")
            return plotkeys
        else:
            return [key for key in self.data.keys() if key not in ['X', 'Y']]


def parse_mix_argument(mix_str):
    """
    解析混合数据参数
    
    Parameters:
    mix_str (str): 混合配置字符串，格式为 "name,data1,data2,..."
    
    Returns:
    list: 解析后的混合配置
    """
    try:
        # 移除可能的方括号和引号
        mix_str = mix_str.strip("[]'\"")
        # 分割字符串
        parts = [part.strip() for part in mix_str.split(',')]
        if len(parts) < 3:
            raise ValueError("混合配置需要至少3个参数")
        return parts
    except Exception as e:
        raise argparse.ArgumentTypeError(f"无效的混合配置 '{mix_str}': {e}")

def parse_keys_to_plot(keys_str):
    """
    解析需要成图的数据
    
    Parameters:
    keys_str (str): 混合配置字符串，格式为 "data1,data2,..."
    
    Returns:
    list: 解析后的数据
    """
    try:
        # 移除可能的方括号和引号
        keys_str = keys_str.strip("[]'\"")
        # 分割字符串
        parts = [part.strip() for part in keys_str.split(',')]
        return parts
    except Exception as e:
        raise argparse.ArgumentTypeError(f"无效的数据键配置 '{keys_str}': {e}")


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
    argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description='STM数据处理器 - 生成高质量的STM图像',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python %(prog)s data.mtd
  python %(prog)s data.mtd --cmap viridis --sigma 1.5 --zoom 10
  python %(prog)s data.mtd --show --dpi 600 --figsize 10 8
  python %(prog)s data.mtd --order 1 --no-save
  
混合数据示例:
  python %(prog)s data.mtd --mix "mix1,water4MOA021LMN1,water4MOA021LMN2"
  python %(prog)s data.mtd --mix "total,water4MOA021LMN1,water4MOA021LMN2,water4MOA021LMN3"
  python %(prog)s data.mtd --mix "combo1,data1,data2" --mix "combo2,data1,data3"

颜色映射选项:
  常用颜色映射: plasma, viridis, hot, coolwarm, jet, gray, rainbow
  更多选项参考: https://matplotlib.org/stable/tutorials/colors/colormaps.html
        '''
    )
    
    # 必需参数
    parser.add_argument('filename', 
                       help='输入数据文件路径 (mtd格式)')
    
    # 数据处理参数
    processing_group = parser.add_argument_group('数据处理参数')
    processing_group.add_argument('--sigma', type=float, default=1.0,
                                help='高斯滤波的sigma值 (默认: 1.0)')
    processing_group.add_argument('--zoom', '--zoom-factor', type=int, default=8,
                                dest='zoom_factor',
                                help='插值缩放因子 (默认: 8)')
    processing_group.add_argument('--order', type=int, default=3, choices=[0, 1, 2, 3, 4, 5],
                                help='插值阶数: 0-最近邻, 1-双线性, 3-双三次 (默认: 3)')
    
    # 混合数据参数
    mix_group = parser.add_argument_group('混合数据参数')
    mix_group.add_argument('--mix', action='append', type=parse_mix_argument,
                         metavar='CONFIG',
                         help='添加混合数据，格式: "名称,数据1,数据2,..." (可多次使用)')
    
    # 图形参数
    plot_group = parser.add_argument_group('图形参数')
    plot_group.add_argument('--cmap', default='plasma',
                          help='颜色映射 (默认: plasma)')
    plot_group.add_argument('--dpi', type=int, default=300,
                          help='图像分辨率DPI (默认: 300)')
    plot_group.add_argument('--figsize', type=float, nargs=2, default=[8, 6],
                          metavar=('WIDTH', 'HEIGHT'),
                          help='图像尺寸 (默认: 8 6)')
    
    # 输出控制参数
    output_group = parser.add_argument_group('输出控制')
    output_group.add_argument('--plotkeys', type=parse_keys_to_plot,
                            metavar='KEYS',
                            help='需要成图的数据列表，格式：“数据1,数据2...”')
    output_group.add_argument('--show', action='store_true',
                            help='显示图像 (默认不显示)')
    output_group.add_argument('--no-save', action='store_true',
                            help='不保存图像文件')
    output_group.add_argument('--output-dir', 
                            help='输出目录 (默认: 当前目录)')
    
    # 其他参数
    parser.add_argument('--summary', action='store_true',
                       help='显示数据摘要后退出')
    
    return parser.parse_args()


def main():
    """
    主函数
    """
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建处理器实例
    processor = STMDataProcessor()
    
    # 加载数据
    if not processor.load_data(args.filename):
        sys.exit(1)
    
    # 添加混合数据
    if args.mix:
        print("=" * 50)
        print("配置混合数据...")
        processor.add_mixed_data(args.mix)
        print("=" * 50)

    # 判断有多少数据需要成图
    #print(args.plotkeys)
    plotkeys = processor.generate_plot_keys(args.plotkeys)
    
    # 显示数据摘要
    processor.summary()
    
    # 如果只显示摘要则退出
    if args.summary:
        print("数据摘要已显示，程序退出。")
        return
    
    # 设置输出目录
    if args.output_dir:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        os.chdir(args.output_dir)
        print(f"输出目录设置为: {args.output_dir}")
    
    # 绘制图像
    print("=" * 50)
    print("开始生成STM图像...")
    print(f"处理参数: sigma={args.sigma}, zoom_factor={args.zoom_factor}, order={args.order}")
    print(f"图形参数: cmap={args.cmap}, dpi={args.dpi}, figsize={args.figsize}")
    print(f"输出控制: show={args.show}, save={not args.no_save},  plotkeys= {plotkeys}")
    if args.mix:
        print(f"混合数据: {len(args.mix)} 个配置")
    print("=" * 50)
    
    try:
        #print("debug0")
        processor.plot_all(
            cmap=args.cmap,
            sigma=args.sigma,
            zoom_factor=args.zoom_factor,
            order=args.order,
            save_fig=not args.no_save,
            show_fig=args.show,
            plotkeys=plotkeys,
            dpi=args.dpi,
            figsize=tuple(args.figsize)
        )
        print("图像生成完成！")
    except Exception as e:
        print(f"生成图像时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
