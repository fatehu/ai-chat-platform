"""
数据库初始化和管理脚本
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database.database import engine, Base, SessionLocal
from app.database.models import Conversation, Message
from sqlalchemy import inspect, text


def check_database_connection():
    """检查数据库连接"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        return False


def create_tables():
    """创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
        
        # 显示创建的表
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📋 已创建的表 ({len(tables)}个):")
        for table in tables:
            print(f"   - {table}")
        
        return True
    except Exception as e:
        print(f"❌ 创建表失败: {str(e)}")
        return False


def drop_tables():
    """删除所有表 (谨慎使用!)"""
    print("\n⚠️  警告: 这将删除所有表和数据!")
    confirm = input("确认删除? (yes/no): ")
    
    if confirm.lower() == 'yes':
        try:
            Base.metadata.drop_all(bind=engine)
            print("✅ 所有表已删除")
            return True
        except Exception as e:
            print(f"❌ 删除表失败: {str(e)}")
            return False
    else:
        print("❌ 操作已取消")
        return False


def show_table_info():
    """显示表结构信息"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("\n📊 数据库表结构:\n")
    
    for table in tables:
        print(f"表: {table}")
        print("-" * 60)
        
        columns = inspector.get_columns(table)
        print(f"{'列名':<20} {'类型':<20} {'可空':<10} {'默认值'}")
        print("-" * 60)
        
        for column in columns:
            nullable = "是" if column['nullable'] else "否"
            default = column['default'] if column['default'] else "-"
            print(f"{column['name']:<20} {str(column['type']):<20} {nullable:<10} {default}")
        
        # 显示索引
        indexes = inspector.get_indexes(table)
        if indexes:
            print("\n索引:")
            for idx in indexes:
                print(f"   - {idx['name']}: {idx['column_names']}")
        
        # 显示外键
        foreign_keys = inspector.get_foreign_keys(table)
        if foreign_keys:
            print("\n外键:")
            for fk in foreign_keys:
                print(f"   - {fk['constrained_columns']} -> "
                      f"{fk['referred_table']}.{fk['referred_columns']}")
        
        print("\n")


def create_sample_data():
    """创建示例数据"""
    db = SessionLocal()
    
    try:
        # 检查是否已有数据
        existing = db.query(Conversation).count()
        if existing > 0:
            print(f"⚠️  数据库中已有 {existing} 个会话")
            confirm = input("是否继续添加示例数据? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ 操作已取消")
                return False
        
        # 创建示例会话
        print("\n创建示例数据...")
        
        # 会话1: 基础对话
        conv1 = Conversation(
            session_id=Conversation.generate_session_id(),
            title="示例对话 - 基础问答",
            model="deepseek-chat",
            enable_rag=False
        )
        db.add(conv1)
        db.flush()
        
        db.add(Message(
            session_id=conv1.session_id,
            role="user",
            content="你好,请介绍一下你自己"
        ))
        db.add(Message(
            session_id=conv1.session_id,
            role="assistant",
            content="你好!我是一个AI助手,可以帮助你解答问题、执行计算、查询信息等。"
        ))
        
        # 会话2: 使用工具
        conv2 = Conversation(
            session_id=Conversation.generate_session_id(),
            title="示例对话 - 计算器",
            model="deepseek-chat",
            enable_rag=False
        )
        db.add(conv2)
        db.flush()
        
        db.add(Message(
            session_id=conv2.session_id,
            role="user",
            content="帮我计算 123 * 456"
        ))
        db.add(Message(
            session_id=conv2.session_id,
            role="assistant",
            content="计算结果: 123 × 456 = 56,088",
            metadata={"used_tool": "calculator"}
        ))
        
        # 会话3: RAG对话
        conv3 = Conversation(
            session_id=Conversation.generate_session_id(),
            title="示例对话 - RAG",
            model="gpt-3.5-turbo",
            enable_rag=True,
            kb_name="demo_kb"
        )
        db.add(conv3)
        
        db.commit()
        
        print(f"✅ 已创建 3 个示例会话")
        print(f"   - {conv1.session_id}: {conv1.title}")
        print(f"   - {conv2.session_id}: {conv2.title}")
        print(f"   - {conv3.session_id}: {conv3.title}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建示例数据失败: {str(e)}")
        return False
    finally:
        db.close()


def show_statistics():
    """显示数据库统计信息"""
    db = SessionLocal()
    
    try:
        conv_count = db.query(Conversation).count()
        msg_count = db.query(Message).count()
        
        print("\n📈 数据库统计:")
        print(f"   会话总数: {conv_count}")
        print(f"   消息总数: {msg_count}")
        
        if conv_count > 0:
            # 按模型统计
            from sqlalchemy import func
            model_stats = db.query(
                Conversation.model,
                func.count(Conversation.id)
            ).group_by(Conversation.model).all()
            
            print("\n   按模型分组:")
            for model, count in model_stats:
                print(f"      - {model}: {count} 个会话")
            
            # RAG使用统计
            rag_enabled = db.query(Conversation).filter(
                Conversation.enable_rag == True
            ).count()
            print(f"\n   启用RAG的会话: {rag_enabled}")
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")
    finally:
        db.close()


def clean_old_conversations(days: int = 30):
    """清理旧会话"""
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_convs = db.query(Conversation).filter(
            Conversation.updated_at < cutoff_date
        ).all()
        
        if not old_convs:
            print(f"✅ 没有 {days} 天前的旧会话")
            return True
        
        print(f"\n找到 {len(old_convs)} 个超过 {days} 天的会话:")
        for conv in old_convs[:5]:  # 只显示前5个
            print(f"   - {conv.title} ({conv.updated_at})")
        
        if len(old_convs) > 5:
            print(f"   ... 还有 {len(old_convs) - 5} 个")
        
        confirm = input(f"\n确认删除这些会话? (yes/no): ")
        
        if confirm.lower() == 'yes':
            for conv in old_convs:
                db.delete(conv)
            db.commit()
            print(f"✅ 已删除 {len(old_convs)} 个旧会话")
            return True
        else:
            print("❌ 操作已取消")
            return False
            
    except Exception as e:
        db.rollback()
        print(f"❌ 清理失败: {str(e)}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库管理工具")
    print("=" * 60 + "\n")
    
    while True:
        print("\n请选择操作:")
        print("1. 检查数据库连接")
        print("2. 创建数据库表")
        print("3. 删除所有表 (危险!)")
        print("4. 显示表结构")
        print("5. 创建示例数据")
        print("6. 显示统计信息")
        print("7. 清理旧会话")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-7): ").strip()
        
        if choice == '1':
            check_database_connection()
        elif choice == '2':
            if check_database_connection():
                create_tables()
        elif choice == '3':
            drop_tables()
        elif choice == '4':
            show_table_info()
        elif choice == '5':
            create_sample_data()
        elif choice == '6':
            show_statistics()
        elif choice == '7':
            days = input("清理多少天前的会话? (默认30): ").strip()
            days = int(days) if days.isdigit() else 30
            clean_old_conversations(days)
        elif choice == '0':
            print("\n👋 再见!")
            break
        else:
            print("❌ 无效选项,请重新选择")


if __name__ == "__main__":
    main()