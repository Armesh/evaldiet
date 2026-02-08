from datetime import datetime
import json
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Numeric,
    DateTime,
    Text,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    text,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# -------------------------------------------------------------------
# Base
# -------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


DEFAULT_SETTINGS = {
    "diet_columns": [
        "Name",
        "Unit",
        "Price",
        "Energy kcal",
        "Protein g",
        "Total lipid (fat) g",
        "Carbohydrate, by difference g",
        "Fiber, total dietary g",
        "Calcium, Ca mg",
        "Iron, Fe mg",
        "Magnesium, Mg mg",
        "Phosphorus, P mg",
        "Potassium, K mg",
        "Sodium, Na mg",
        "Zinc, Zn mg",
        "Copper, Cu mg",
        "Selenium, Se µg",
        "Vitamin C, total ascorbic acid mg",
        "Thiamin mg",
        "Riboflavin mg",
        "Niacin mg",
        "Pantothenic acid mg",
        "Vitamin B-6 mg",
        "Folate, total µg",
        "Vitamin B-12 µg",
        "Choline, total mg",
        "Vitamin A, RAE µg",
        "Cholesterol mg",
        "Fatty acids, total saturated g",
        "Vitamin E (alpha-tocopherol) mg",
        "Vitamin K, total µg",
        "Vitamin D (D2 + D3), International Units IU",
        "diet_name",
        "fdc_id",
        "quantity",
        "sort_order",
        "color",
    ],
    "diet_hide_rda_ul_values": False,
    "diet_rda_threshold": 100,
    "diet_ul_threshold": 100,
    "food-dominant-carb": "#4c65b8",
    "food-dominant-fat": "#98823e",
    "food-dominant-protein": "#490303",
}
DEFAULT_SETTINGS_JSON = json.dumps(DEFAULT_SETTINGS, ensure_ascii=False)


# -------------------------------------------------------------------
# Users
# -------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'" + DEFAULT_SETTINGS_JSON.replace("'", "''") + "'::jsonb"),
    )

    foods: Mapped[list["Food"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_settings_gin", "settings", postgresql_using="gin"),
    )


# -------------------------------------------------------------------
# Foods (FULL COLUMN SET)
# -------------------------------------------------------------------

class Food(Base):
    __tablename__ = "foods"

    user_id: Mapped[int] = mapped_column("user_id", Integer, nullable=False)
    fdc_id: Mapped[int] = mapped_column("fdc_id", Integer, nullable=False)
    name: Mapped[str] = mapped_column("Name", String(255), nullable=False)
    serving_size: Mapped[int] = mapped_column("Serving Size", Integer, nullable=False, server_default=text("100"))
    unit: Mapped[str] = mapped_column("Unit", String(12), nullable=False, server_default=text("'grams'"))
    price: Mapped[float] = mapped_column("Price", Numeric(10, 2), nullable=False, server_default=text("999.00"))
    energy_kj: Mapped[float] = mapped_column("Energy kJ", Numeric(10, 1), nullable=False, server_default=text("0.0"))
    energy_kcal: Mapped[float] = mapped_column("Energy kcal", Numeric(10, 1), nullable=False, server_default=text("0.0"))
    protein_g: Mapped[float] = mapped_column("Protein g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    total_lipid_fat_g: Mapped[float] = mapped_column("Total lipid (fat) g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    carbohydrate_by_difference_g: Mapped[float] = mapped_column("Carbohydrate, by difference g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fiber_total_dietary_g: Mapped[float] = mapped_column("Fiber, total dietary g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    calcium_ca_mg: Mapped[float] = mapped_column("Calcium, Ca mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    iron_fe_mg: Mapped[float] = mapped_column("Iron, Fe mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    magnesium_mg_mg: Mapped[float] = mapped_column("Magnesium, Mg mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    phosphorus_p_mg: Mapped[float] = mapped_column("Phosphorus, P mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    potassium_k_mg: Mapped[float] = mapped_column("Potassium, K mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    sodium_na_mg: Mapped[float] = mapped_column("Sodium, Na mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    zinc_zn_mg: Mapped[float] = mapped_column("Zinc, Zn mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    copper_cu_mg: Mapped[float] = mapped_column("Copper, Cu mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    selenium_se_g: Mapped[float] = mapped_column("Selenium, Se µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_c_total_ascorbic_acid_mg: Mapped[float] = mapped_column("Vitamin C, total ascorbic acid mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    thiamin_mg: Mapped[float] = mapped_column("Thiamin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    riboflavin_mg: Mapped[float] = mapped_column("Riboflavin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    niacin_mg: Mapped[float] = mapped_column("Niacin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    pantothenic_acid_mg: Mapped[float] = mapped_column("Pantothenic acid mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_b_6_mg: Mapped[float] = mapped_column("Vitamin B-6 mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    folate_total_g: Mapped[float] = mapped_column("Folate, total µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    folic_acid_g: Mapped[float] = mapped_column("Folic acid µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    folate_food_g: Mapped[float] = mapped_column("Folate, food µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    folate_dfe_g: Mapped[float] = mapped_column("Folate, DFE µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_b_12_g: Mapped[float] = mapped_column("Vitamin B-12 µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_b_12_added_g: Mapped[float] = mapped_column("Vitamin B-12, added µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    choline_total_mg: Mapped[float] = mapped_column("Choline, total mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_a_rae_g: Mapped[float] = mapped_column("Vitamin A, RAE µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    retinol_g: Mapped[float] = mapped_column("Retinol µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_a_iu_iu: Mapped[float] = mapped_column("Vitamin A, IU IU", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    cholesterol_mg: Mapped[float] = mapped_column("Cholesterol mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_saturated_g: Mapped[float] = mapped_column("Fatty acids, total saturated g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_monounsaturated_g: Mapped[float] = mapped_column("Fatty acids, total monounsaturated g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_polyunsaturated_g: Mapped[float] = mapped_column("Fatty acids, total polyunsaturated g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tryptophan_g: Mapped[float] = mapped_column("Tryptophan g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    threonine_g: Mapped[float] = mapped_column("Threonine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    isoleucine_g: Mapped[float] = mapped_column("Isoleucine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    leucine_g: Mapped[float] = mapped_column("Leucine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    lysine_g: Mapped[float] = mapped_column("Lysine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    methionine_g: Mapped[float] = mapped_column("Methionine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    cystine_g: Mapped[float] = mapped_column("Cystine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    phenylalanine_g: Mapped[float] = mapped_column("Phenylalanine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tyrosine_g: Mapped[float] = mapped_column("Tyrosine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    valine_g: Mapped[float] = mapped_column("Valine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    arginine_g: Mapped[float] = mapped_column("Arginine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    histidine_g: Mapped[float] = mapped_column("Histidine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    aspartic_acid_g: Mapped[float] = mapped_column("Aspartic acid g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    glutamic_acid_g: Mapped[float] = mapped_column("Glutamic acid g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    glycine_g: Mapped[float] = mapped_column("Glycine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    proline_g: Mapped[float] = mapped_column("Proline g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    serine_g: Mapped[float] = mapped_column("Serine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    nitrogen_g: Mapped[float] = mapped_column("Nitrogen g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    manganese_mn_mg: Mapped[float] = mapped_column("Manganese, Mn mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    total_fat_nlea_g: Mapped[float] = mapped_column("Total fat (NLEA) g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_d_d2_d3_international_units_iu: Mapped[float] = mapped_column("Vitamin D (D2 + D3), International Units IU", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_d_d2_d3_g: Mapped[float] = mapped_column("Vitamin D (D2 + D3) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_d3_cholecalciferol_g: Mapped[float] = mapped_column("Vitamin D3 (cholecalciferol) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_e_alpha_tocopherol_mg: Mapped[float] = mapped_column("Vitamin E (alpha-tocopherol) mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocopherol_beta_mg: Mapped[float] = mapped_column("Tocopherol, beta mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocopherol_gamma_mg: Mapped[float] = mapped_column("Tocopherol, gamma mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocopherol_delta_mg: Mapped[float] = mapped_column("Tocopherol, delta mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocotrienol_alpha_mg: Mapped[float] = mapped_column("Tocotrienol, alpha mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocotrienol_beta_mg: Mapped[float] = mapped_column("Tocotrienol, beta mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocotrienol_gamma_mg: Mapped[float] = mapped_column("Tocotrienol, gamma mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    tocotrienol_delta_mg: Mapped[float] = mapped_column("Tocotrienol, delta mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_e_added_mg: Mapped[float] = mapped_column("Vitamin E, added mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_k_phylloquinone_g: Mapped[float] = mapped_column("Vitamin K (phylloquinone) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_k_menaquinone_4_g: Mapped[float] = mapped_column("Vitamin K (Menaquinone-4) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_k_menaquinone_7_g: Mapped[float] = mapped_column("Vitamin K (Menaquinone-7) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_k_total_g: Mapped[float] = mapped_column("Vitamin K, total µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    vitamin_k_dihydrophylloquinone_g: Mapped[float] = mapped_column("Vitamin K (Dihydrophylloquinone) µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_trans_g: Mapped[float] = mapped_column("Fatty acids, total trans g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_trans_monoenoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-monoenoic g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_trans_dienoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-dienoic g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    sugars_total_including_nlea_g: Mapped[float] = mapped_column("Sugars, total including NLEA g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    sucrose_g: Mapped[float] = mapped_column("Sucrose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    glucose_g: Mapped[float] = mapped_column("Glucose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fructose_g: Mapped[float] = mapped_column("Fructose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    lactose_g: Mapped[float] = mapped_column("Lactose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    maltose_g: Mapped[float] = mapped_column("Maltose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    galactose_g: Mapped[float] = mapped_column("Galactose g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    betaine_mg: Mapped[float] = mapped_column("Betaine mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    carotene_beta_g: Mapped[float] = mapped_column("Carotene, beta µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    carotene_alpha_g: Mapped[float] = mapped_column("Carotene, alpha µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    cryptoxanthin_beta_g: Mapped[float] = mapped_column("Cryptoxanthin, beta µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    lycopene_g: Mapped[float] = mapped_column("Lycopene µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    lutein_zeaxanthin_g: Mapped[float] = mapped_column("Lutein + zeaxanthin µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    phytosterols_mg: Mapped[float] = mapped_column("Phytosterols mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    alanine_g: Mapped[float] = mapped_column("Alanine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    theobromine_mg: Mapped[float] = mapped_column("Theobromine mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    starch_g: Mapped[float] = mapped_column("Starch g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    hydroxyproline_g: Mapped[float] = mapped_column("Hydroxyproline g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fluoride_f_g: Mapped[float] = mapped_column("Fluoride, F µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    fatty_acids_total_trans_polyenoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-polyenoic g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    stigmasterol_mg: Mapped[float] = mapped_column("Stigmasterol mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    campesterol_mg: Mapped[float] = mapped_column("Campesterol mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    beta_sitosterol_mg: Mapped[float] = mapped_column("Beta-sitosterol mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    alcohol_ethyl_g: Mapped[float] = mapped_column("Alcohol, ethyl g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    caffeine_mg: Mapped[float] = mapped_column("Caffeine mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    sugars_added_g: Mapped[float] = mapped_column("Sugars, added g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    sugars_total_g: Mapped[float] = mapped_column("Sugars, Total g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    total_sugars_g: Mapped[float] = mapped_column("Total Sugars g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    biotin_g: Mapped[float] = mapped_column("Biotin µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    cysteine_g: Mapped[float] = mapped_column("Cysteine g", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    daidzein_mg: Mapped[float] = mapped_column("Daidzein mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    genistein_mg: Mapped[float] = mapped_column("Genistein mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    daidzin_mg: Mapped[float] = mapped_column("Daidzin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    genistin_mg: Mapped[float] = mapped_column("Genistin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    glycitin_mg: Mapped[float] = mapped_column("Glycitin mg", Numeric(10, 3), nullable=False, server_default=text("0.000"))
    iodine_i_g: Mapped[float] = mapped_column("Iodine, I µg", Numeric(10, 3), nullable=False, server_default=text("0.000"))

    user: Mapped["User"] = relationship(back_populates="foods")

    __table_args__ = (
        Index("ix_foods_user_id", "user_id"),
        Index("ix_foods_fdc_id", "fdc_id"),
        Index("ix_foods_name", "Name"),
        UniqueConstraint("user_id", "Name"),
        UniqueConstraint("user_id", "fdc_id"),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    __mapper_args__ = {"primary_key": [user_id, fdc_id]}

# -------------------------------------------------------------------
# Diets
# -------------------------------------------------------------------

class Diet(Base):
    __tablename__ = "diets"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    diet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fdc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(32))

    __table_args__ = (
        Index("ix_diets_user_id", "user_id"),
        Index("ix_diets_diet_name", "diet_name"),
        Index("ix_diets_fdc_id", "fdc_id"),
        UniqueConstraint("user_id", "diet_name", "fdc_id", "quantity", "sort_order"),
        ForeignKeyConstraint(
            ["user_id", "fdc_id"],
            ["foods.user_id", "foods.fdc_id"],
            ondelete="CASCADE",
        ),
    )

    __mapper_args__ = {"primary_key": [user_id, diet_name, fdc_id, quantity, sort_order]}


# -------------------------------------------------------------------
# RDA
# -------------------------------------------------------------------

class RDA(Base):
    __tablename__ = "rda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    nutrient: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_rda_user_id", "user_id"),
        UniqueConstraint("user_id", "nutrient"),
    )


# -------------------------------------------------------------------
# UL
# -------------------------------------------------------------------

class UL(Base):
    __tablename__ = "ul"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    nutrient: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_ul_user_id", "user_id"),
        UniqueConstraint("user_id", "nutrient"),
    )
