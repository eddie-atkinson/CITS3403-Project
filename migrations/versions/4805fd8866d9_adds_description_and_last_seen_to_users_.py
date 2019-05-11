"""adds description and last seen to users tabble

Revision ID: 4805fd8866d9
Revises: 1cdcf0588329
Create Date: 2019-05-11 12:14:58.499236

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4805fd8866d9'
down_revision = '1cdcf0588329'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('description', sa.String(length=240), nullable=True))
    op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'last_seen')
    op.drop_column('user', 'description')
    # ### end Alembic commands ###
