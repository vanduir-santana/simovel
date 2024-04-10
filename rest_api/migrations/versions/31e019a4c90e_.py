"""empty message

Revision ID: 31e019a4c90e
Revises: cdc4124d4ad1
Create Date: 2022-06-02 20:34:41.157969

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '31e019a4c90e'
down_revision = 'cdc4124d4ad1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('simulacao', sa.Column('tipo_imovel', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('simulacao', 'tipo_imovel')
    # ### end Alembic commands ###