import ast

code = """
def thuc_hien_phep_cong():
    try:
        # Nhập số thứ nhất từ bàn phím
        so_thu_nhat = int(input(""))
        
        # Nhập số thứ hai từ bàn phím
        so_thu_hai = int(input(""))
        
        # Tính tổng
        ket_qua = so_thu_nhat + so_thu_hai
        
        # In kết quả ra màn hình
        print(ket_qua)
        
    except ValueError:
        print("Lỗi: Vui lòng chỉ nhập số nguyên hợp lệ!")

if __name__ == "__main__":
    thuc_hien_phep_cong()
"""

class RenameTransformer(ast.NodeTransformer):
    def __init__(self):
        self.names = {}
        self.counter = 0

    def get_name(self, original_id):
        if original_id not in self.names:
            self.names[original_id] = f'_v{self.counter}'
            self.counter += 1
        return self.names[original_id]

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Load)):
            # Don't rename builtins roughly
            if node.id not in ('print', 'int', 'input', 'ValueError', 'str', 'float', 'list', 'dict'):
                node.id = self.get_name(node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self.get_name(node.name)
        self.generic_visit(node)
        return node
        
    def visit_arg(self, node):
        node.arg = self.get_name(node.arg)
        return node

tree = ast.parse(code)
RenameTransformer().visit(tree)
ast.fix_missing_locations(tree)
print(ast.unparse(tree))
