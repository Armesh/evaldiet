from datetime import datetime
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# -------------------------------------------------------------------
# Base
# -------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


DEFAULT_SETTINGS_JSON = (
    "{\"diet_columns\": [\"Name\", \"Unit\", \"Price\", \"Energy kcal\", \"Protein g\", "
    "\"Total lipid (fat) g\", \"Carbohydrate, by difference g\", \"Fiber, total dietary g\", "
    "\"Calcium, Ca mg\", \"Iron, Fe mg\", \"Magnesium, Mg mg\", \"Phosphorus, P mg\", "
    "\"Potassium, K mg\", \"Sodium, Na mg\", \"Zinc, Zn mg\", \"Copper, Cu mg\", "
    "\"Selenium, Se µg\", \"Vitamin C, total ascorbic acid mg\", \"Thiamin mg\", "
    "\"Riboflavin mg\", \"Niacin mg\", \"Pantothenic acid mg\", \"Vitamin B-6 mg\", "
    "\"Folate, total µg\", \"Vitamin B-12 µg\", \"Choline, total mg\", \"Vitamin A, RAE µg\", "
    "\"Cholesterol mg\", \"Fatty acids, total saturated g\", \"Vitamin E (alpha-tocopherol) mg\", "
    "\"Vitamin K, total µg\", \"Vitamin D (D2 + D3), International Units IU\", \"diet_name\", "
    "\"fdc_id\", \"quantity\", \"sort_order\", \"color\"], \"diet_hide_rda_ul_values\": false, "
    "\"diet_rda_threshold\": 100, \"diet_ul_threshold\": 100, \"food-dominant-carb\": \"#4c65b8\", "
    "\"food-dominant-fat\": \"#98823e\", \"food-dominant-protein\": \"#490303\"}"
)


# -------------------------------------------------------------------
# Users
# -------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text(f"'{DEFAULT_SETTINGS_JSON.replace(\"'\", \"''\")}'::jsonb"),
    )

    foods: Mapped[list["Food"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# -------------------------------------------------------------------
# Foods (FULL COLUMN SET)
# -------------------------------------------------------------------

class Food(Base):
    __tablename__ = "foods"

    user_id: Mapped[int] = mapped_column("user_id", Integer, nullable=False)
    fdc_id: Mapped[int] = mapped_column("fdc_id", Integer, nullable=False)
    name: Mapped[str] = mapped_column("Name", Text, nullable=False)
    serving_size: Mapped[int] = mapped_column("Serving Size", Integer, nullable=False, server_default=text("100"))
    unit: Mapped[str] = mapped_column("Unit", Text, nullable=False, server_default=text("'grams'"))
    price: Mapped[float] = mapped_column("Price", Float, nullable=False, server_default=text("999"))
    energy_kj: Mapped[float] = mapped_column("Energy kJ", Float, nullable=False, server_default=text("0"))
    energy_kcal: Mapped[float] = mapped_column("Energy kcal", Float, nullable=False, server_default=text("0"))
    protein_g: Mapped[float] = mapped_column("Protein g", Float, nullable=False, server_default=text("0"))
    total_lipid_fat_g: Mapped[float] = mapped_column("Total lipid (fat) g", Float, nullable=False, server_default=text("0"))
    carbohydrate_by_difference_g: Mapped[float] = mapped_column("Carbohydrate, by difference g", Float, nullable=False, server_default=text("0"))
    fiber_total_dietary_g: Mapped[float] = mapped_column("Fiber, total dietary g", Float, nullable=False, server_default=text("0"))
    calcium_ca_mg: Mapped[float] = mapped_column("Calcium, Ca mg", Float, nullable=False, server_default=text("0"))
    iron_fe_mg: Mapped[float] = mapped_column("Iron, Fe mg", Float, nullable=False, server_default=text("0"))
    magnesium_mg_mg: Mapped[float] = mapped_column("Magnesium, Mg mg", Float, nullable=False, server_default=text("0"))
    phosphorus_p_mg: Mapped[float] = mapped_column("Phosphorus, P mg", Float, nullable=False, server_default=text("0"))
    potassium_k_mg: Mapped[float] = mapped_column("Potassium, K mg", Float, nullable=False, server_default=text("0"))
    sodium_na_mg: Mapped[float] = mapped_column("Sodium, Na mg", Float, nullable=False, server_default=text("0"))
    zinc_zn_mg: Mapped[float] = mapped_column("Zinc, Zn mg", Float, nullable=False, server_default=text("0"))
    copper_cu_mg: Mapped[float] = mapped_column("Copper, Cu mg", Float, nullable=False, server_default=text("0"))
    selenium_se_g: Mapped[float] = mapped_column("Selenium, Se µg", Float, nullable=False, server_default=text("0"))
    vitamin_c_total_ascorbic_acid_mg: Mapped[float] = mapped_column("Vitamin C, total ascorbic acid mg", Float, nullable=False, server_default=text("0"))
    thiamin_mg: Mapped[float] = mapped_column("Thiamin mg", Float, nullable=False, server_default=text("0"))
    riboflavin_mg: Mapped[float] = mapped_column("Riboflavin mg", Float, nullable=False, server_default=text("0"))
    niacin_mg: Mapped[float] = mapped_column("Niacin mg", Float, nullable=False, server_default=text("0"))
    pantothenic_acid_mg: Mapped[float] = mapped_column("Pantothenic acid mg", Float, nullable=False, server_default=text("0"))
    vitamin_b_6_mg: Mapped[float] = mapped_column("Vitamin B-6 mg", Float, nullable=False, server_default=text("0"))
    folate_total_g: Mapped[float] = mapped_column("Folate, total µg", Float, nullable=False, server_default=text("0"))
    folic_acid_g: Mapped[float] = mapped_column("Folic acid µg", Float, nullable=False, server_default=text("0"))
    folate_food_g: Mapped[float] = mapped_column("Folate, food µg", Float, nullable=False, server_default=text("0"))
    folate_dfe_g: Mapped[float] = mapped_column("Folate, DFE µg", Float, nullable=False, server_default=text("0"))
    vitamin_b_12_g: Mapped[float] = mapped_column("Vitamin B-12 µg", Float, nullable=False, server_default=text("0"))
    vitamin_b_12_added_g: Mapped[float] = mapped_column("Vitamin B-12, added µg", Float, nullable=False, server_default=text("0"))
    choline_total_mg: Mapped[float] = mapped_column("Choline, total mg", Float, nullable=False, server_default=text("0"))
    vitamin_a_rae_g: Mapped[float] = mapped_column("Vitamin A, RAE µg", Float, nullable=False, server_default=text("0"))
    retinol_g: Mapped[float] = mapped_column("Retinol µg", Float, nullable=False, server_default=text("0"))
    vitamin_a_iu_iu: Mapped[float] = mapped_column("Vitamin A, IU IU", Float, nullable=False, server_default=text("0"))
    cholesterol_mg: Mapped[float] = mapped_column("Cholesterol mg", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_saturated_g: Mapped[float] = mapped_column("Fatty acids, total saturated g", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_monounsaturated_g: Mapped[float] = mapped_column("Fatty acids, total monounsaturated g", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_polyunsaturated_g: Mapped[float] = mapped_column("Fatty acids, total polyunsaturated g", Float, nullable=False, server_default=text("0"))
    tryptophan_g: Mapped[float] = mapped_column("Tryptophan g", Float, nullable=False, server_default=text("0"))
    threonine_g: Mapped[float] = mapped_column("Threonine g", Float, nullable=False, server_default=text("0"))
    isoleucine_g: Mapped[float] = mapped_column("Isoleucine g", Float, nullable=False, server_default=text("0"))
    leucine_g: Mapped[float] = mapped_column("Leucine g", Float, nullable=False, server_default=text("0"))
    lysine_g: Mapped[float] = mapped_column("Lysine g", Float, nullable=False, server_default=text("0"))
    methionine_g: Mapped[float] = mapped_column("Methionine g", Float, nullable=False, server_default=text("0"))
    cystine_g: Mapped[float] = mapped_column("Cystine g", Float, nullable=False, server_default=text("0"))
    phenylalanine_g: Mapped[float] = mapped_column("Phenylalanine g", Float, nullable=False, server_default=text("0"))
    tyrosine_g: Mapped[float] = mapped_column("Tyrosine g", Float, nullable=False, server_default=text("0"))
    valine_g: Mapped[float] = mapped_column("Valine g", Float, nullable=False, server_default=text("0"))
    arginine_g: Mapped[float] = mapped_column("Arginine g", Float, nullable=False, server_default=text("0"))
    histidine_g: Mapped[float] = mapped_column("Histidine g", Float, nullable=False, server_default=text("0"))
    aspartic_acid_g: Mapped[float] = mapped_column("Aspartic acid g", Float, nullable=False, server_default=text("0"))
    glutamic_acid_g: Mapped[float] = mapped_column("Glutamic acid g", Float, nullable=False, server_default=text("0"))
    glycine_g: Mapped[float] = mapped_column("Glycine g", Float, nullable=False, server_default=text("0"))
    proline_g: Mapped[float] = mapped_column("Proline g", Float, nullable=False, server_default=text("0"))
    serine_g: Mapped[float] = mapped_column("Serine g", Float, nullable=False, server_default=text("0"))
    nitrogen_g: Mapped[float] = mapped_column("Nitrogen g", Float, nullable=False, server_default=text("0"))
    manganese_mn_mg: Mapped[float] = mapped_column("Manganese, Mn mg", Float, nullable=False, server_default=text("0"))
    total_fat_nlea_g: Mapped[float] = mapped_column("Total fat (NLEA) g", Float, nullable=False, server_default=text("0"))
    vitamin_d_d2_d3_international_units_iu: Mapped[float] = mapped_column("Vitamin D (D2 + D3), International Units IU", Float, nullable=False, server_default=text("0"))
    vitamin_d_d2_d3_g: Mapped[float] = mapped_column("Vitamin D (D2 + D3) µg", Float, nullable=False, server_default=text("0"))
    vitamin_d3_cholecalciferol_g: Mapped[float] = mapped_column("Vitamin D3 (cholecalciferol) µg", Float, nullable=False, server_default=text("0"))
    vitamin_e_alpha_tocopherol_mg: Mapped[float] = mapped_column("Vitamin E (alpha-tocopherol) mg", Float, nullable=False, server_default=text("0"))
    tocopherol_beta_mg: Mapped[float] = mapped_column("Tocopherol, beta mg", Float, nullable=False, server_default=text("0"))
    tocopherol_gamma_mg: Mapped[float] = mapped_column("Tocopherol, gamma mg", Float, nullable=False, server_default=text("0"))
    tocopherol_delta_mg: Mapped[float] = mapped_column("Tocopherol, delta mg", Float, nullable=False, server_default=text("0"))
    tocotrienol_alpha_mg: Mapped[float] = mapped_column("Tocotrienol, alpha mg", Float, nullable=False, server_default=text("0"))
    tocotrienol_beta_mg: Mapped[float] = mapped_column("Tocotrienol, beta mg", Float, nullable=False, server_default=text("0"))
    tocotrienol_gamma_mg: Mapped[float] = mapped_column("Tocotrienol, gamma mg", Float, nullable=False, server_default=text("0"))
    tocotrienol_delta_mg: Mapped[float] = mapped_column("Tocotrienol, delta mg", Float, nullable=False, server_default=text("0"))
    vitamin_e_added_mg: Mapped[float] = mapped_column("Vitamin E, added mg", Float, nullable=False, server_default=text("0"))
    vitamin_k_phylloquinone_g: Mapped[float] = mapped_column("Vitamin K (phylloquinone) µg", Float, nullable=False, server_default=text("0"))
    vitamin_k_menaquinone_4_g: Mapped[float] = mapped_column("Vitamin K (Menaquinone-4) µg", Float, nullable=False, server_default=text("0"))
    vitamin_k_menaquinone_7_g: Mapped[float] = mapped_column("Vitamin K (Menaquinone-7) µg", Float, nullable=False, server_default=text("0"))
    vitamin_k_total_g: Mapped[float] = mapped_column("Vitamin K, total µg", Float, nullable=False, server_default=text("0"))
    vitamin_k_dihydrophylloquinone_g: Mapped[float] = mapped_column("Vitamin K (Dihydrophylloquinone) µg", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_trans_g: Mapped[float] = mapped_column("Fatty acids, total trans g", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_trans_monoenoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-monoenoic g", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_trans_dienoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-dienoic g", Float, nullable=False, server_default=text("0"))
    sugars_total_including_nlea_g: Mapped[float] = mapped_column("Sugars, total including NLEA g", Float, nullable=False, server_default=text("0"))
    sucrose_g: Mapped[float] = mapped_column("Sucrose g", Float, nullable=False, server_default=text("0"))
    glucose_g: Mapped[float] = mapped_column("Glucose g", Float, nullable=False, server_default=text("0"))
    fructose_g: Mapped[float] = mapped_column("Fructose g", Float, nullable=False, server_default=text("0"))
    lactose_g: Mapped[float] = mapped_column("Lactose g", Float, nullable=False, server_default=text("0"))
    maltose_g: Mapped[float] = mapped_column("Maltose g", Float, nullable=False, server_default=text("0"))
    galactose_g: Mapped[float] = mapped_column("Galactose g", Float, nullable=False, server_default=text("0"))
    betaine_mg: Mapped[float] = mapped_column("Betaine mg", Float, nullable=False, server_default=text("0"))
    carotene_beta_g: Mapped[float] = mapped_column("Carotene, beta µg", Float, nullable=False, server_default=text("0"))
    carotene_alpha_g: Mapped[float] = mapped_column("Carotene, alpha µg", Float, nullable=False, server_default=text("0"))
    cryptoxanthin_beta_g: Mapped[float] = mapped_column("Cryptoxanthin, beta µg", Float, nullable=False, server_default=text("0"))
    lycopene_g: Mapped[float] = mapped_column("Lycopene µg", Float, nullable=False, server_default=text("0"))
    lutein_zeaxanthin_g: Mapped[float] = mapped_column("Lutein + zeaxanthin µg", Float, nullable=False, server_default=text("0"))
    phytosterols_mg: Mapped[float] = mapped_column("Phytosterols mg", Float, nullable=False, server_default=text("0"))
    alanine_g: Mapped[float] = mapped_column("Alanine g", Float, nullable=False, server_default=text("0"))
    theobromine_mg: Mapped[float] = mapped_column("Theobromine mg", Float, nullable=False, server_default=text("0"))
    starch_g: Mapped[float] = mapped_column("Starch g", Float, nullable=False, server_default=text("0"))
    hydroxyproline_g: Mapped[float] = mapped_column("Hydroxyproline g", Float, nullable=False, server_default=text("0"))
    fluoride_f_g: Mapped[float] = mapped_column("Fluoride, F µg", Float, nullable=False, server_default=text("0"))
    fatty_acids_total_trans_polyenoic_g: Mapped[float] = mapped_column("Fatty acids, total trans-polyenoic g", Float, nullable=False, server_default=text("0"))
    stigmasterol_mg: Mapped[float] = mapped_column("Stigmasterol mg", Float, nullable=False, server_default=text("0"))
    campesterol_mg: Mapped[float] = mapped_column("Campesterol mg", Float, nullable=False, server_default=text("0"))
    beta_sitosterol_mg: Mapped[float] = mapped_column("Beta-sitosterol mg", Float, nullable=False, server_default=text("0"))
    alcohol_ethyl_g: Mapped[float] = mapped_column("Alcohol, ethyl g", Float, nullable=False, server_default=text("0"))
    caffeine_mg: Mapped[float] = mapped_column("Caffeine mg", Float, nullable=False, server_default=text("0"))
    sugars_added_g: Mapped[float] = mapped_column("Sugars, added g", Float, nullable=False, server_default=text("0"))
    sugars_total_g: Mapped[float] = mapped_column("Sugars, Total g", Float, nullable=False, server_default=text("0"))
    total_sugars_g: Mapped[float] = mapped_column("Total Sugars g", Float, nullable=False, server_default=text("0"))
    biotin_g: Mapped[float] = mapped_column("Biotin µg", Float, nullable=False, server_default=text("0"))
    cysteine_g: Mapped[float] = mapped_column("Cysteine g", Float, nullable=False, server_default=text("0"))
    daidzein_mg: Mapped[float] = mapped_column("Daidzein mg", Float, nullable=False, server_default=text("0"))
    genistein_mg: Mapped[float] = mapped_column("Genistein mg", Float, nullable=False, server_default=text("0"))
    daidzin_mg: Mapped[float] = mapped_column("Daidzin mg", Float, nullable=False, server_default=text("0"))
    genistin_mg: Mapped[float] = mapped_column("Genistin mg", Float, nullable=False, server_default=text("0"))
    glycitin_mg: Mapped[float] = mapped_column("Glycitin mg", Float, nullable=False, server_default=text("0"))
    energy_atwater_general_factors_kcal: Mapped[float] = mapped_column("Energy (Atwater General Factors) kcal", Float, nullable=False, server_default=text("0"))
    energy_atwater_specific_factors_kcal: Mapped[float] = mapped_column("Energy (Atwater Specific Factors) kcal", Float, nullable=False, server_default=text("0"))
    iodine_i_g: Mapped[float] = mapped_column("Iodine, I µg", Float, nullable=False, server_default=text("0"))

    user: Mapped["User"] = relationship(back_populates="foods")

    __table_args__ = (
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
    diet_name: Mapped[str] = mapped_column(Text, nullable=False)
    fdc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
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
    __tablename__ = "RDA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    nutrient: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "nutrient"),
    )


# -------------------------------------------------------------------
# UL
# -------------------------------------------------------------------

class UL(Base):
    __tablename__ = "UL"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    nutrient: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "nutrient"),
    )
