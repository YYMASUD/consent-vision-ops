from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None

def upgrade():
 op.create_table("schema_info",sa.Column("id",sa.Integer,primary_key=True),sa.Column("created_at",sa.DateTime,nullable=False))
def downgrade(): op.drop_table("schema_info")
